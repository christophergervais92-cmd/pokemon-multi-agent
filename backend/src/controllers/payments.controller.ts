import { Response } from 'express';
import { PaymentService } from '../services/payment.service';
import { AuthRequest } from '../middleware/auth.middleware';

export class PaymentController {
  static async createPaymentIntent(req: AuthRequest, res: Response) {
    try {
      const { amount } = req.body;
      const result = await PaymentService.createPaymentIntent(req.userId!, amount);
      res.json(result);
    } catch (error: any) {
      console.error('Payment intent error:', error);
      res.status(500).json({ error: { message: 'Failed to create payment intent', status: 500 } });
    }
  }

  static async getPaymentMethods(req: AuthRequest, res: Response) {
    try {
      const methods = await PaymentService.getPaymentMethods(req.userId!);
      res.json(methods);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to fetch payment methods', status: 500 } });
    }
  }

  static async savePaymentMethod(req: AuthRequest, res: Response) {
    try {
      const { paymentMethodId } = req.body;
      const method = await PaymentService.savePaymentMethod(req.userId!, paymentMethodId);
      res.status(201).json(method);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to save payment method', status: 500 } });
    }
  }

  static async deletePaymentMethod(req: AuthRequest, res: Response) {
    try {
      const { id } = req.params;
      await PaymentService.deletePaymentMethod(req.userId!, id);
      res.json({ success: true });
    } catch (error: any) {
      if (error.message === 'Payment method not found') {
        return res.status(404).json({ error: { message: error.message, status: 404 } });
      }
      res.status(500).json({ error: { message: 'Failed to delete payment method', status: 500 } });
    }
  }

  static async setDefaultPaymentMethod(req: AuthRequest, res: Response) {
    try {
      const { id } = req.params;
      const method = await PaymentService.setDefaultPaymentMethod(req.userId!, id);
      res.json(method);
    } catch (error: any) {
      res.status(500).json({ error: { message: 'Failed to set default payment method', status: 500 } });
    }
  }
}
