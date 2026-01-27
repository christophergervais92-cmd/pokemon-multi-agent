import { Request, Response } from 'express';
import { AuthService } from '../services/auth.service';

export class AuthController {
  static async register(req: Request, res: Response) {
    try {
      const { name, email, phone, password } = req.body;
      const result = await AuthService.register({ name, email, phone, password });
      res.status(201).json(result);
    } catch (error: any) {
      if (error.message === 'Email already registered') {
        return res.status(409).json({ error: { message: error.message, status: 409 } });
      }
      res.status(500).json({ error: { message: 'Registration failed', status: 500 } });
    }
  }

  static async login(req: Request, res: Response) {
    try {
      const { email, password } = req.body;
      const result = await AuthService.login(email, password);
      res.json(result);
    } catch (error: any) {
      if (error.message === 'Invalid credentials') {
        return res.status(401).json({ error: { message: error.message, status: 401 } });
      }
      res.status(500).json({ error: { message: 'Login failed', status: 500 } });
    }
  }

  static async refresh(req: Request, res: Response) {
    try {
      const { refreshToken } = req.body;
      const tokens = await AuthService.refreshToken(refreshToken);
      res.json(tokens);
    } catch (error: any) {
      res.status(401).json({ error: { message: 'Invalid refresh token', status: 401 } });
    }
  }

  static async logout(req: Request, res: Response) {
    // In a production app, you might want to blacklist the token
    res.json({ message: 'Logged out successfully' });
  }
}
