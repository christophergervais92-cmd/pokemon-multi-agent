import { Response } from 'express';
import { OrderService } from '../services/order.service';
import { PaymentService } from '../services/payment.service';
import { AuthRequest } from '../middleware/auth.middleware';

export class OrderController {
  static async createOrder(req: AuthRequest, res: Response) {
    try {
      const {
        restaurantId,
        items,
        deliveryAddress,
        deliveryLatitude,
        deliveryLongitude,
        specialInstructions,
        tip,
        paymentMethodId
      } = req.body;

      // Create payment intent first
      // Note: In production, you'd want to verify the payment was successful
      // before creating the order

      const order = await OrderService.createOrder({
        userId: req.userId!,
        restaurantId,
        items,
        deliveryAddress,
        deliveryLatitude,
        deliveryLongitude,
        specialInstructions,
        tip: tip || 0,
        stripePaymentId: paymentMethodId
      });

      res.status(201).json(order);
    } catch (error: any) {
      if (error.message.includes('Minimum order')) {
        return res.status(400).json({ error: { message: error.message, status: 400 } });
      }
      if (error.message.includes('not found')) {
        return res.status(404).json({ error: { message: error.message, status: 404 } });
      }
      console.error('Create order error:', error);
      res.status(500).json({ error: { message: 'Failed to create order', status: 500 } });
    }
  }

  static async getOrders(req: AuthRequest, res: Response) {
    try {
      const orders = await OrderService.getOrders(req.userId!);
      res.json(orders);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to fetch orders', status: 500 } });
    }
  }

  static async getActiveOrders(req: AuthRequest, res: Response) {
    try {
      const orders = await OrderService.getActiveOrders(req.userId!);
      res.json(orders);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to fetch active orders', status: 500 } });
    }
  }

  static async getOrderById(req: AuthRequest, res: Response) {
    try {
      const { id } = req.params;
      const order = await OrderService.getOrderById(id, req.userId!);
      res.json(order);
    } catch (error: any) {
      if (error.message === 'Order not found') {
        return res.status(404).json({ error: { message: error.message, status: 404 } });
      }
      res.status(500).json({ error: { message: 'Failed to fetch order', status: 500 } });
    }
  }

  static async rateOrder(req: AuthRequest, res: Response) {
    try {
      const { id } = req.params;
      const { rating, comment } = req.body;
      
      const review = await OrderService.rateOrder(id, req.userId!, rating, comment);
      res.json(review);
    } catch (error: any) {
      if (error.message.includes('not found') || error.message.includes('not eligible')) {
        return res.status(404).json({ error: { message: error.message, status: 404 } });
      }
      if (error.message === 'Order already reviewed') {
        return res.status(409).json({ error: { message: error.message, status: 409 } });
      }
      res.status(500).json({ error: { message: 'Failed to rate order', status: 500 } });
    }
  }

  static async reorder(req: AuthRequest, res: Response) {
    try {
      const { id } = req.params;
      const items = await OrderService.reorder(id, req.userId!);
      res.json(items);
    } catch (error: any) {
      if (error.message === 'Order not found') {
        return res.status(404).json({ error: { message: error.message, status: 404 } });
      }
      res.status(500).json({ error: { message: 'Failed to get reorder items', status: 500 } });
    }
  }
}
