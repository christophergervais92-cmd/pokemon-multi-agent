import { prisma } from '../config/database';
import { redis } from '../config/redis';

interface RestaurantFilters {
  category?: string;
  search?: string;
  latitude?: number;
  longitude?: number;
  maxDistance?: number; // in km
  minRating?: number;
  sortBy?: 'rating' | 'deliveryTime' | 'distance' | 'deliveryFee';
  limit?: number;
  offset?: number;
}

export class RestaurantService {
  static async getRestaurants(filters: RestaurantFilters) {
    const {
      category,
      search,
      latitude,
      longitude,
      minRating,
      sortBy = 'rating',
      limit = 20,
      offset = 0
    } = filters;

    const where: any = {
      isOpen: true
    };

    if (category && category !== 'all') {
      where.category = {
        equals: category,
        mode: 'insensitive'
      };
    }

    if (search) {
      where.OR = [
        { name: { contains: search, mode: 'insensitive' } },
        { description: { contains: search, mode: 'insensitive' } },
        { category: { contains: search, mode: 'insensitive' } }
      ];
    }

    if (minRating) {
      where.rating = { gte: minRating };
    }

    let orderBy: any = {};
    switch (sortBy) {
      case 'rating':
        orderBy = { rating: 'desc' };
        break;
      case 'deliveryTime':
        orderBy = { deliveryTimeMin: 'asc' };
        break;
      case 'deliveryFee':
        orderBy = { deliveryFee: 'asc' };
        break;
      default:
        orderBy = { rating: 'desc' };
    }

    const [restaurants, total] = await Promise.all([
      prisma.restaurant.findMany({
        where,
        orderBy,
        take: limit,
        skip: offset,
        select: {
          id: true,
          name: true,
          description: true,
          imageUrl: true,
          coverImageUrl: true,
          category: true,
          rating: true,
          reviewCount: true,
          deliveryTimeMin: true,
          deliveryTimeMax: true,
          deliveryFee: true,
          minimumOrder: true,
          latitude: true,
          longitude: true,
          address: true,
          isOpen: true,
          openingTime: true,
          closingTime: true
        }
      }),
      prisma.restaurant.count({ where })
    ]);

    // Calculate distance if user location provided
    let results = restaurants;
    if (latitude && longitude) {
      results = restaurants.map(r => ({
        ...r,
        distance: this.calculateDistance(latitude, longitude, r.latitude, r.longitude)
      }));

      if (sortBy === 'distance') {
        results.sort((a: any, b: any) => a.distance - b.distance);
      }
    }

    return {
      restaurants: results,
      total,
      hasMore: offset + restaurants.length < total
    };
  }

  static async getRestaurantById(id: string, userId?: string) {
    // Try cache first
    const cacheKey = `restaurant:${id}`;
    const cached = await redis.get(cacheKey);
    
    if (cached) {
      const restaurant = JSON.parse(cached);
      if (userId) {
        restaurant.isFavorite = await this.isFavorite(userId, id);
      }
      return restaurant;
    }

    const restaurant = await prisma.restaurant.findUnique({
      where: { id },
      include: {
        menuItems: {
          where: { isAvailable: true },
          include: {
            options: {
              include: {
                choices: true
              }
            }
          },
          orderBy: [
            { isPopular: 'desc' },
            { category: 'asc' },
            { name: 'asc' }
          ]
        }
      }
    });

    if (!restaurant) {
      throw new Error('Restaurant not found');
    }

    // Cache for 5 minutes
    await redis.setex(cacheKey, 300, JSON.stringify(restaurant));

    if (userId) {
      (restaurant as any).isFavorite = await this.isFavorite(userId, id);
    }

    return restaurant;
  }

  static async getMenu(restaurantId: string) {
    const cacheKey = `menu:${restaurantId}`;
    const cached = await redis.get(cacheKey);
    
    if (cached) {
      return JSON.parse(cached);
    }

    const menuItems = await prisma.menuItem.findMany({
      where: {
        restaurantId,
        isAvailable: true
      },
      include: {
        options: {
          include: {
            choices: true
          }
        }
      },
      orderBy: [
        { isPopular: 'desc' },
        { category: 'asc' },
        { name: 'asc' }
      ]
    });

    // Group by category
    const menuByCategory: { [key: string]: any[] } = {};
    for (const item of menuItems) {
      if (!menuByCategory[item.category]) {
        menuByCategory[item.category] = [];
      }
      menuByCategory[item.category].push(item);
    }

    const menu = Object.entries(menuByCategory).map(([category, items]) => ({
      category,
      items
    }));

    // Cache for 5 minutes
    await redis.setex(cacheKey, 300, JSON.stringify(menu));

    return menu;
  }

  static async toggleFavorite(userId: string, restaurantId: string) {
    const existing = await prisma.favorite.findUnique({
      where: {
        userId_restaurantId: {
          userId,
          restaurantId
        }
      }
    });

    if (existing) {
      await prisma.favorite.delete({
        where: { id: existing.id }
      });
      return { isFavorite: false };
    }

    await prisma.favorite.create({
      data: {
        userId,
        restaurantId
      }
    });

    return { isFavorite: true };
  }

  static async getFavorites(userId: string) {
    const favorites = await prisma.favorite.findMany({
      where: { userId },
      include: {
        restaurant: {
          select: {
            id: true,
            name: true,
            description: true,
            imageUrl: true,
            category: true,
            rating: true,
            reviewCount: true,
            deliveryTimeMin: true,
            deliveryTimeMax: true,
            deliveryFee: true,
            isOpen: true
          }
        }
      }
    });

    return favorites.map(f => f.restaurant);
  }

  private static async isFavorite(userId: string, restaurantId: string): Promise<boolean> {
    const favorite = await prisma.favorite.findUnique({
      where: {
        userId_restaurantId: {
          userId,
          restaurantId
        }
      }
    });
    return !!favorite;
  }

  private static calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
    const R = 6371; // Earth's radius in km
    const dLat = this.toRad(lat2 - lat1);
    const dLon = this.toRad(lon2 - lon1);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRad(lat1)) * Math.cos(this.toRad(lat2)) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  private static toRad(deg: number): number {
    return deg * (Math.PI / 180);
  }
}
