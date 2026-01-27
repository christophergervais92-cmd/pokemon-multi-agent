import { Router } from 'express';
import { body } from 'express-validator';
import { UserController } from '../controllers/users.controller';
import { validate } from '../middleware/validation.middleware';
import { authMiddleware } from '../middleware/auth.middleware';

const router = Router();

// All user routes require authentication
router.use(authMiddleware);

// Profile
router.get('/me', UserController.getCurrentUser);
router.put(
  '/me',
  validate([
    body('name').optional().trim().notEmpty().withMessage('Name cannot be empty'),
    body('phone').optional().trim()
  ]),
  UserController.updateProfile
);

// Addresses
router.get('/me/addresses', UserController.getAddresses);
router.post(
  '/me/addresses',
  validate([
    body('label').trim().notEmpty().withMessage('Label is required'),
    body('street').trim().notEmpty().withMessage('Street is required'),
    body('city').trim().notEmpty().withMessage('City is required'),
    body('state').trim().notEmpty().withMessage('State is required'),
    body('zipCode').trim().notEmpty().withMessage('Zip code is required'),
    body('apartment').optional().trim(),
    body('latitude').optional().isFloat(),
    body('longitude').optional().isFloat(),
    body('isDefault').optional().isBoolean()
  ]),
  UserController.addAddress
);
router.delete('/me/addresses/:id', UserController.deleteAddress);
router.put('/me/addresses/:id/default', UserController.setDefaultAddress);

// Favorites
router.get('/me/favorites', UserController.getFavorites);
router.post('/me/favorites/:restaurantId', UserController.toggleFavorite);

export default router;
