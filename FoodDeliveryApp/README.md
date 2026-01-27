# FoodDash - Food Delivery iOS App

A full-featured food delivery iOS application built with SwiftUI and a Node.js backend, similar to Uber Eats.

## Features

### Customer App
- User authentication (email/password, social login ready)
- Restaurant discovery with search and filters
- Category-based browsing
- Restaurant menus with item customization
- Cart management
- Checkout with Stripe payment integration
- Real-time order tracking with MapKit
- Order history and reordering
- Restaurant reviews and ratings
- User profile management
- Saved addresses and payment methods
- Favorites

## Tech Stack

### iOS App
- **UI**: SwiftUI (iOS 15+)
- **Architecture**: MVVM with Combine
- **Networking**: URLSession with async/await
- **Maps**: MapKit
- **Real-time**: WebSocket for order tracking
- **Security**: Keychain for secure token storage

### Backend
- **Runtime**: Node.js with Express
- **Language**: TypeScript
- **Database**: PostgreSQL with Prisma ORM
- **Cache**: Redis
- **Real-time**: Socket.io
- **Payments**: Stripe
- **Authentication**: JWT

## Project Structure

```
FoodDeliveryApp/
├── FoodDeliveryApp/
│   ├── App/                    # App entry point
│   ├── Core/                   # Network, Auth, Location
│   ├── Features/               # Feature modules
│   │   ├── Auth/
│   │   ├── Home/
│   │   ├── Restaurant/
│   │   ├── Cart/
│   │   ├── Checkout/
│   │   ├── OrderTracking/
│   │   ├── Orders/
│   │   ├── Search/
│   │   └── Profile/
│   ├── Models/                 # Data models
│   └── Components/             # Reusable UI components
│
backend/
├── src/
│   ├── config/                 # Database and Redis config
│   ├── routes/                 # API routes
│   ├── controllers/            # Request handlers
│   ├── services/               # Business logic
│   ├── middleware/             # Auth and validation
│   └── websocket/              # Real-time events
├── prisma/
│   └── schema.prisma           # Database schema
└── package.json
```

## Getting Started

### Prerequisites
- Xcode 15+
- Node.js 18+
- PostgreSQL
- Redis

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

4. Set up the database:
```bash
npm run db:push
```

5. Start the development server:
```bash
npm run dev
```

### iOS App Setup

1. Open `FoodDeliveryApp.xcodeproj` in Xcode

2. Update the API base URL in `Core/Network/APIClient.swift` if needed

3. Build and run the app on a simulator or device

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token

### Restaurants
- `GET /api/restaurants` - List restaurants
- `GET /api/restaurants/:id` - Restaurant details
- `GET /api/restaurants/:id/menu` - Restaurant menu

### Orders
- `POST /api/orders` - Create order
- `GET /api/orders` - Order history
- `GET /api/orders/:id` - Order details
- `POST /api/orders/:id/rate` - Rate order

### User
- `GET /api/users/me` - Current user
- `PUT /api/users/me` - Update profile
- `GET /api/users/me/addresses` - Saved addresses
- `POST /api/users/me/addresses` - Add address

### Payments
- `POST /api/payments/create-intent` - Create payment intent
- `GET /api/payments/methods` - Payment methods

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret
JWT_REFRESH_SECRET=your-refresh-secret
STRIPE_SECRET_KEY=sk_test_...
PORT=3000
```

## Architecture

The app follows MVVM architecture:
- **Views**: SwiftUI views for UI
- **ViewModels**: ObservableObjects for state and logic
- **Models**: Codable structs for data
- **Services**: Network and business logic

## Real-time Updates

Order tracking uses WebSocket connections to receive:
- Order status updates
- Driver location updates
- ETA updates

## License

MIT
