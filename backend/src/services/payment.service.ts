import Stripe from 'stripe';
import { prisma } from '../config/database';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16'
});

export class PaymentService {
  static async createPaymentIntent(userId: string, amount: number, currency = 'usd') {
    // Get or create Stripe customer
    const user = await prisma.user.findUnique({
      where: { id: userId }
    });

    if (!user) {
      throw new Error('User not found');
    }

    // Create payment intent
    const paymentIntent = await stripe.paymentIntents.create({
      amount: Math.round(amount * 100), // Convert to cents
      currency,
      metadata: {
        userId
      }
    });

    return {
      clientSecret: paymentIntent.client_secret,
      paymentIntentId: paymentIntent.id
    };
  }

  static async confirmPayment(paymentIntentId: string) {
    const paymentIntent = await stripe.paymentIntents.retrieve(paymentIntentId);
    
    return {
      status: paymentIntent.status,
      succeeded: paymentIntent.status === 'succeeded'
    };
  }

  static async savePaymentMethod(userId: string, paymentMethodId: string) {
    const paymentMethod = await stripe.paymentMethods.retrieve(paymentMethodId);

    if (paymentMethod.type !== 'card') {
      throw new Error('Only card payment methods are supported');
    }

    const card = paymentMethod.card!;

    // Check if this card is already saved
    const existing = await prisma.paymentMethod.findFirst({
      where: {
        userId,
        last4: card.last4,
        brand: card.brand
      }
    });

    if (existing) {
      return existing;
    }

    // Check if this is the first payment method
    const count = await prisma.paymentMethod.count({
      where: { userId }
    });

    const saved = await prisma.paymentMethod.create({
      data: {
        userId,
        stripeMethodId: paymentMethodId,
        type: 'card',
        last4: card.last4,
        brand: card.brand || 'unknown',
        isDefault: count === 0
      }
    });

    return saved;
  }

  static async getPaymentMethods(userId: string) {
    return prisma.paymentMethod.findMany({
      where: { userId },
      orderBy: { isDefault: 'desc' }
    });
  }

  static async deletePaymentMethod(userId: string, paymentMethodId: string) {
    const method = await prisma.paymentMethod.findFirst({
      where: {
        id: paymentMethodId,
        userId
      }
    });

    if (!method) {
      throw new Error('Payment method not found');
    }

    await prisma.paymentMethod.delete({
      where: { id: paymentMethodId }
    });

    // If deleted was default, set another as default
    if (method.isDefault) {
      const another = await prisma.paymentMethod.findFirst({
        where: { userId }
      });

      if (another) {
        await prisma.paymentMethod.update({
          where: { id: another.id },
          data: { isDefault: true }
        });
      }
    }

    return { success: true };
  }

  static async setDefaultPaymentMethod(userId: string, paymentMethodId: string) {
    // Unset current default
    await prisma.paymentMethod.updateMany({
      where: { userId, isDefault: true },
      data: { isDefault: false }
    });

    // Set new default
    const method = await prisma.paymentMethod.update({
      where: { id: paymentMethodId },
      data: { isDefault: true }
    });

    return method;
  }
}
