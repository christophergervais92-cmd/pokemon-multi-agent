import { prisma } from '../config/database';
import { redis } from '../config/redis';
import { emitOrderUpdate } from '../websocket/orderTracking';
import { OrderStatus } from '@prisma/client';

interface CreateOrderData {
  userId: string;
  restaurantId: string;
  items: Array<{
    menuItemId: string;
    quantity: number;
    selectedOptions?: any;
    specialNotes?: string;
  }>;
  deliveryAddress: {
    street: string;
    apartment?: string;
    city: string;
    state: string;
    zipCode: string;
  };
  deliveryLatitude?: number;
  deliveryLongitude?: number;
  specialInstructions?: string;
  tip: number;
  stripePaymentId?: string;
}

export class OrderService {
  static async createOrder(data: CreateOrderData) {
    const restaurant = await prisma.restaurant.findUnique({
      where: { id: data.restaurantId }
    });

    if (!restaurant) {
      throw new Error('Restaurant not found');
    }

    // Calculate prices
    let subtotal = 0;
    const orderItems = [];

    for (const item of data.items) {
      const menuItem = await prisma.menuItem.findUnique({
        where: { id: item.menuItemId },
        include: {
          options: {
            include: { choices: true }
          }
        }
      });

      if (!menuItem) {
        throw new Error(`Menu item ${item.menuItemId} not found`);
      }

      let unitPrice = Number(menuItem.price);

      // Add option prices
      if (item.selectedOptions) {
        for (const [optionId, choiceIds] of Object.entries(item.selectedOptions)) {
          const option = menuItem.options.find(o => o.id === optionId);
          if (option) {
            for (const choiceId of choiceIds as string[]) {
              const choice = option.choices.find(c => c.id === choiceId);
              if (choice) {
                unitPrice += Number(choice.price);
              }
            }
          }
        }
      }

      const totalPrice = unitPrice * item.quantity;
      subtotal += totalPrice;

      orderItems.push({
        menuItemId: item.menuItemId,
        name: menuItem.name,
        quantity: item.quantity,
        unitPrice,
        totalPrice,
        selectedOptions: item.selectedOptions,
        specialNotes: item.specialNotes
      });
    }

    const deliveryFee = Number(restaurant.deliveryFee);
    const serviceFee = subtotal * 0.05; // 5% service fee
    const tip = data.tip || 0;
    const total = subtotal + deliveryFee + serviceFee + tip;

    // Check minimum order
    if (subtotal < Number(restaurant.minimumOrder)) {
      throw new Error(`Minimum order is $${restaurant.minimumOrder}`);
    }

    // Calculate estimated delivery
    const estimatedDelivery = new Date();
    estimatedDelivery.setMinutes(
      estimatedDelivery.getMinutes() + restaurant.deliveryTimeMax
    );

    const order = await prisma.order.create({
      data: {
        userId: data.userId,
        restaurantId: data.restaurantId,
        status: 'PENDING',
        subtotal,
        deliveryFee,
        serviceFee,
        tip,
        discount: 0,
        total,
        deliveryAddress: data.deliveryAddress,
        deliveryLatitude: data.deliveryLatitude,
        deliveryLongitude: data.deliveryLongitude,
        specialInstructions: data.specialInstructions,
        estimatedDelivery,
        stripePaymentId: data.stripePaymentId,
        items: {
          create: orderItems
        }
      },
      include: {
        restaurant: {
          select: {
            id: true,
            name: true,
            imageUrl: true
          }
        },
        items: true
      }
    });

    return order;
  }

  static async getOrders(userId: string, status?: OrderStatus) {
    const where: any = { userId };
    
    if (status) {
      where.status = status;
    }

    const orders = await prisma.order.findMany({
      where,
      include: {
        restaurant: {
          select: {
            id: true,
            name: true,
            imageUrl: true
          }
        },
        items: true,
        driver: {
          select: {
            id: true,
            name: true,
            phone: true,
            avatarUrl: true,
            vehicleType: true,
            rating: true
          }
        }
      },
      orderBy: { createdAt: 'desc' }
    });

    return orders;
  }

  static async getOrderById(orderId: string, userId: string) {
    const order = await prisma.order.findFirst({
      where: {
        id: orderId,
        userId
      },
      include: {
        restaurant: {
          select: {
            id: true,
            name: true,
            imageUrl: true,
            address: true,
            phone: true
          }
        },
        items: true,
        driver: {
          select: {
            id: true,
            name: true,
            phone: true,
            avatarUrl: true,
            vehicleType: true,
            rating: true,
            latitude: true,
            longitude: true
          }
        },
        review: true
      }
    });

    if (!order) {
      throw new Error('Order not found');
    }

    return order;
  }

  static async updateOrderStatus(orderId: string, status: OrderStatus) {
    const order = await prisma.order.update({
      where: { id: orderId },
      data: { status }
    });

    // Emit real-time update
    await emitOrderUpdate(orderId, status);

    return order;
  }

  static async assignDriver(orderId: string, driverId: string) {
    const order = await prisma.order.update({
      where: { id: orderId },
      data: {
        driverId,
        status: 'OUT_FOR_DELIVERY'
      },
      include: {
        driver: {
          select: {
            id: true,
            name: true,
            phone: true,
            avatarUrl: true,
            vehicleType: true,
            rating: true
          }
        }
      }
    });

    await emitOrderUpdate(orderId, 'OUT_FOR_DELIVERY');

    return order;
  }

  static async rateOrder(orderId: string, userId: string, rating: number, comment?: string) {
    const order = await prisma.order.findFirst({
      where: {
        id: orderId,
        userId,
        status: 'DELIVERED'
      }
    });

    if (!order) {
      throw new Error('Order not found or not eligible for review');
    }

    // Check if already reviewed
    const existingReview = await prisma.review.findUnique({
      where: { orderId }
    });

    if (existingReview) {
      throw new Error('Order already reviewed');
    }

    // Create review
    const review = await prisma.review.create({
      data: {
        userId,
        restaurantId: order.restaurantId,
        orderId,
        rating,
        comment
      }
    });

    // Update restaurant rating
    const reviews = await prisma.review.findMany({
      where: { restaurantId: order.restaurantId }
    });

    const avgRating = reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length;

    await prisma.restaurant.update({
      where: { id: order.restaurantId },
      data: {
        rating: avgRating,
        reviewCount: reviews.length
      }
    });

    // Invalidate restaurant cache
    await redis.del(`restaurant:${order.restaurantId}`);

    return review;
  }

  static async getActiveOrders(userId: string) {
    return this.getOrders(userId).then(orders =>
      orders.filter(o =>
        ['PENDING', 'CONFIRMED', 'PREPARING', 'READY_FOR_PICKUP', 'OUT_FOR_DELIVERY'].includes(o.status)
      )
    );
  }

  static async reorder(orderId: string, userId: string) {
    const order = await this.getOrderById(orderId, userId);
    
    // Return items that can be added to cart
    return order.items.map(item => ({
      menuItemId: item.menuItemId,
      name: item.name,
      quantity: item.quantity,
      selectedOptions: item.selectedOptions,
      specialNotes: item.specialNotes
    }));
  }
}
