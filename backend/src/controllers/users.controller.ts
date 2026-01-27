import { Response } from 'express';
import { AuthService } from '../services/auth.service';
import { RestaurantService } from '../services/restaurant.service';
import { AuthRequest } from '../middleware/auth.middleware';
import { prisma } from '../config/database';

export class UserController {
  static async getCurrentUser(req: AuthRequest, res: Response) {
    try {
      const user = await AuthService.getUser(req.userId!);
      res.json(user);
    } catch (error: any) {
      res.status(404).json({ error: { message: 'User not found', status: 404 } });
    }
  }

  static async updateProfile(req: AuthRequest, res: Response) {
    try {
      const { name, phone } = req.body;
      const user = await AuthService.updateUser(req.userId!, { name, phone });
      res.json(user);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to update profile', status: 500 } });
    }
  }

  static async getAddresses(req: AuthRequest, res: Response) {
    try {
      const addresses = await prisma.address.findMany({
        where: { userId: req.userId! },
        orderBy: { isDefault: 'desc' }
      });
      res.json(addresses);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to fetch addresses', status: 500 } });
    }
  }

  static async addAddress(req: AuthRequest, res: Response) {
    try {
      const { label, street, apartment, city, state, zipCode, latitude, longitude, isDefault } = req.body;

      // If setting as default, unset other defaults
      if (isDefault) {
        await prisma.address.updateMany({
          where: { userId: req.userId!, isDefault: true },
          data: { isDefault: false }
        });
      }

      // Check if this is the first address
      const count = await prisma.address.count({
        where: { userId: req.userId! }
      });

      const address = await prisma.address.create({
        data: {
          userId: req.userId!,
          label,
          street,
          apartment,
          city,
          state,
          zipCode,
          latitude,
          longitude,
          isDefault: isDefault || count === 0
        }
      });

      res.status(201).json(address);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to add address', status: 500 } });
    }
  }

  static async deleteAddress(req: AuthRequest, res: Response) {
    try {
      const { id } = req.params;

      const address = await prisma.address.findFirst({
        where: { id, userId: req.userId! }
      });

      if (!address) {
        return res.status(404).json({ error: { message: 'Address not found', status: 404 } });
      }

      await prisma.address.delete({ where: { id } });

      // If deleted was default, set another as default
      if (address.isDefault) {
        const another = await prisma.address.findFirst({
          where: { userId: req.userId! }
        });

        if (another) {
          await prisma.address.update({
            where: { id: another.id },
            data: { isDefault: true }
          });
        }
      }

      res.json({ success: true });
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to delete address', status: 500 } });
    }
  }

  static async setDefaultAddress(req: AuthRequest, res: Response) {
    try {
      const { id } = req.params;

      // Unset current default
      await prisma.address.updateMany({
        where: { userId: req.userId!, isDefault: true },
        data: { isDefault: false }
      });

      // Set new default
      const address = await prisma.address.update({
        where: { id },
        data: { isDefault: true }
      });

      res.json(address);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to set default address', status: 500 } });
    }
  }

  static async getFavorites(req: AuthRequest, res: Response) {
    try {
      const favorites = await RestaurantService.getFavorites(req.userId!);
      res.json(favorites);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to fetch favorites', status: 500 } });
    }
  }

  static async toggleFavorite(req: AuthRequest, res: Response) {
    try {
      const { restaurantId } = req.params;
      const result = await RestaurantService.toggleFavorite(req.userId!, restaurantId);
      res.json(result);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to update favorite', status: 500 } });
    }
  }
}
