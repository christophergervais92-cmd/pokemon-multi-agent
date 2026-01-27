import { Server as HttpServer } from 'http';
import { Server, Socket } from 'socket.io';
import jwt from 'jsonwebtoken';
import { redis } from '../config/redis';

let io: Server;

export const initWebSocket = (server: HttpServer) => {
  io = new Server(server, {
    cors: {
      origin: '*',
      methods: ['GET', 'POST']
    }
  });

  io.use(async (socket, next) => {
    try {
      const token = socket.handshake.query.token as string;
      if (!token) {
        return next(new Error('Authentication required'));
      }

      const decoded = jwt.verify(token, process.env.JWT_SECRET!) as { userId: string };
      socket.data.userId = decoded.userId;
      next();
    } catch {
      next(new Error('Invalid token'));
    }
  });

  io.on('connection', (socket: Socket) => {
    console.log(`Client connected: ${socket.id}`);

    // Join order room
    socket.on('join_order', (orderId: string) => {
      socket.join(`order:${orderId}`);
      console.log(`Socket ${socket.id} joined order:${orderId}`);
    });

    // Leave order room
    socket.on('leave_order', (orderId: string) => {
      socket.leave(`order:${orderId}`);
    });

    // Subscribe to driver updates
    socket.on('subscribe_driver', (driverId: string) => {
      socket.join(`driver:${driverId}`);
    });

    socket.on('disconnect', () => {
      console.log(`Client disconnected: ${socket.id}`);
    });
  });

  // Subscribe to Redis for order updates
  subscribeToOrderUpdates();

  return io;
};

const subscribeToOrderUpdates = async () => {
  const subscriber = redis.duplicate();
  
  subscriber.subscribe('order_updates', (err) => {
    if (err) {
      console.error('Redis subscription error:', err);
    }
  });

  subscriber.on('message', (channel, message) => {
    try {
      const data = JSON.parse(message);
      
      if (data.type === 'order_status') {
        io.to(`order:${data.orderId}`).emit('order_status', {
          orderId: data.orderId,
          status: data.status,
          timestamp: new Date().toISOString()
        });
      }
      
      if (data.type === 'driver_location') {
        io.to(`order:${data.orderId}`).emit('driver_location', {
          orderId: data.orderId,
          latitude: data.latitude,
          longitude: data.longitude,
          timestamp: new Date().toISOString()
        });
      }
      
      if (data.type === 'eta_update') {
        io.to(`order:${data.orderId}`).emit('eta_update', {
          orderId: data.orderId,
          eta: data.eta,
          timestamp: new Date().toISOString()
        });
      }
    } catch (error) {
      console.error('Error processing order update:', error);
    }
  });
};

export const emitOrderUpdate = async (orderId: string, status: string) => {
  await redis.publish('order_updates', JSON.stringify({
    type: 'order_status',
    orderId,
    status
  }));
};

export const emitDriverLocation = async (orderId: string, latitude: number, longitude: number) => {
  await redis.publish('order_updates', JSON.stringify({
    type: 'driver_location',
    orderId,
    latitude,
    longitude
  }));
};

export const emitEtaUpdate = async (orderId: string, eta: number) => {
  await redis.publish('order_updates', JSON.stringify({
    type: 'eta_update',
    orderId,
    eta
  }));
};

export const getIO = () => io;
