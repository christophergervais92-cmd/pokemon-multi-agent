import dotenv from 'dotenv';
dotenv.config();

import http from 'http';
import { app } from './app';
import { initWebSocket } from './websocket/orderTracking';
import { prisma } from './config/database';
import { redis } from './config/redis';

const PORT = process.env.PORT || 3000;

const server = http.createServer(app);

// Initialize WebSocket
initWebSocket(server);

async function start() {
  try {
    // Test database connection
    await prisma.$connect();
    console.log('✅ Database connected');

    // Test Redis connection
    await redis.ping();
    console.log('✅ Redis connected');

    server.listen(PORT, () => {
      console.log(`🚀 Server running on port ${PORT}`);
      console.log(`📡 WebSocket ready`);
    });
  } catch (error) {
    console.error('❌ Failed to start server:', error);
    process.exit(1);
  }
}

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received. Shutting down gracefully...');
  await prisma.$disconnect();
  await redis.quit();
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

start();
