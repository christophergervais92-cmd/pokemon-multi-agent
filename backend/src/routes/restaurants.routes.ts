import { Router } from 'express';
import { RestaurantController } from '../controllers/restaurants.controller';
import { authMiddleware, optionalAuthMiddleware } from '../middleware/auth.middleware';

const router = Router();

// Public routes (with optional auth for favorites)
router.get('/', optionalAuthMiddleware, RestaurantController.getRestaurants);
router.get('/:id', optionalAuthMiddleware, RestaurantController.getRestaurantById);
router.get('/:id/menu', RestaurantController.getMenu);

// Protected routes
router.post('/:id/favorite', authMiddleware, RestaurantController.toggleFavorite);

export default router;
