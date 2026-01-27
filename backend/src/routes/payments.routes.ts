import { Router } from 'express';
import { body } from 'express-validator';
import { PaymentController } from '../controllers/payments.controller';
import { validate } from '../middleware/validation.middleware';
import { authMiddleware } from '../middleware/auth.middleware';

const router = Router();

// All payment routes require authentication
router.use(authMiddleware);

router.post(
  '/create-intent',
  validate([
    body('amount').isFloat({ min: 0.5 }).withMessage('Amount must be at least $0.50')
  ]),
  PaymentController.createPaymentIntent
);

router.get('/methods', PaymentController.getPaymentMethods);

router.post(
  '/methods',
  validate([
    body('paymentMethodId').notEmpty().withMessage('Payment method ID is required')
  ]),
  PaymentController.savePaymentMethod
);

router.delete('/methods/:id', PaymentController.deletePaymentMethod);
router.put('/methods/:id/default', PaymentController.setDefaultPaymentMethod);

export default router;
