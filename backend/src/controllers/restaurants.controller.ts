import { Response } from 'express';
import { RestaurantService } from '../services/restaurant.service';
import { AuthRequest } from '../middleware/auth.middleware';

export class RestaurantController {
  static async getRestaurants(req: AuthRequest, res: Response) {
    try {
      const {
        category,
        search,
        latitude,
        longitude,
        minRating,
        sortBy,
        limit,
        offset
      } = req.query;

      const result = await RestaurantService.getRestaurants({
        category: category as string,
        search: search as string,
        latitude: latitude ? parseFloat(latitude as string) : undefined,
        longitude: longitude ? parseFloat(longitude as string) : undefined,
        minRating: minRating ? parseFloat(minRating as string) : undefined,
        sortBy: sortBy as any,
        limit: limit ? parseInt(limit as string) : undefined,
        offset: offset ? parseInt(offset as string) : undefined
      });

      res.json(result);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to fetch restaurants', status: 500 } });
    }
  }

  static async getRestaurantById(req: AuthRequest, res: Response) {
    try {
      const { id } = req.params;
      const restaurant = await RestaurantService.getRestaurantById(id, req.userId);
      res.json(restaurant);
    } catch (error: any) {
      if (error.message === 'Restaurant not found') {
        return res.status(404).json({ error: { message: error.message, status: 404 } });
      }
      res.status(500).json({ error: { message: 'Failed to fetch restaurant', status: 500 } });
    }
  }

  static async getMenu(req: AuthRequest, res: Response) {
    try {
      const { id } = req.params;
      const menu = await RestaurantService.getMenu(id);
      res.json(menu);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to fetch menu', status: 500 } });
    }
  }

  static async toggleFavorite(req: AuthRequest, res: Response) {
    try {
      const { id } = req.params;
      const result = await RestaurantService.toggleFavorite(req.userId!, id);
      res.json(result);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to update favorite', status: 500 } });
    }
  }
}
