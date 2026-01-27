import { Router } from 'express';
import { body } from 'express-validator';
import { OrderController } from '../controllers/orders.controller';
import { validate } from '../middleware/validation.middleware';
import { authMiddleware } from '../middleware/auth.middleware';

const router = Router();

// All order routes require authentication
router.use(authMiddleware);

router.post(
  '/',
  validate([
    body('restaurantId').notEmpty().withMessage('Restaurant ID is required'),
    body('items').isArray({ min: 1 }).withMessage('At least one item is required'),
    body('items.*.menuItemId').notEmpty().withMessage('Menu item ID is required'),
    body('items.*.quantity').isInt({ min: 1 }).withMessage('Quantity must be at least 1'),
    body('deliveryAddress.street').notEmpty().withMessage('Street is required'),
    body('deliveryAddress.city').notEmpty().withMessage('City is required'),
    body('deliveryAddress.state').notEmpty().withMessage('State is required'),
    body('deliveryAddress.zipCode').notEmpty().withMessage('Zip code is required'),
    body('tip').optional().isFloat({ min: 0 }).withMessage('Tip must be a positive number'),
    body('paymentMethodId').notEmpty().withMessage('Payment method is required')
  ]),
  OrderController.createOrder
);

router.get('/', OrderController.getOrders);
router.get('/active', OrderController.getActiveOrders);
router.get('/:id', OrderController.getOrderById);

router.post(
  '/:id/rate',
  validate([
    body('rating').isInt({ min: 1, max: 5 }).withMessage('Rating must be between 1 and 5'),
    body('comment').optional().trim()
  ]),
  OrderController.rateOrder
);

router.post('/:id/reorder', OrderController.reorder);

export default router;
