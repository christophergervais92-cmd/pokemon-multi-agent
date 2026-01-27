import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';

const prisma = new PrismaClient();

async function main() {
  console.log('Seeding database...');

  // Create test user
  const passwordHash = await bcrypt.hash('password123', 12);
  
  const user = await prisma.user.upsert({
    where: { email: 'test@example.com' },
    update: {},
    create: {
      email: 'test@example.com',
      name: 'Test User',
      phone: '+15551234567',
      passwordHash,
    },
  });

  console.log('Created user:', user.email);

  // Create test address
  await prisma.address.upsert({
    where: { id: 'addr-1' },
    update: {},
    create: {
      id: 'addr-1',
      userId: user.id,
      label: 'Home',
      street: '123 Main Street',
      apartment: 'Apt 4B',
      city: 'San Francisco',
      state: 'CA',
      zipCode: '94102',
      latitude: 37.7749,
      longitude: -122.4194,
      isDefault: true,
    },
  });

  // Create restaurants
  const restaurants = [
    {
      id: 'rest-1',
      name: 'Pizza Palace',
      description: 'The best pizza in town with fresh ingredients and authentic recipes.',
      imageUrl: 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=400',
      coverImageUrl: 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800',
      category: 'Pizza',
      rating: 4.5,
      reviewCount: 234,
      deliveryTimeMin: 20,
      deliveryTimeMax: 35,
      deliveryFee: 2.99,
      minimumOrder: 15.00,
      latitude: 37.7749,
      longitude: -122.4194,
      address: '123 Main St, San Francisco, CA',
      isOpen: true,
      openingTime: '10:00',
      closingTime: '22:00',
    },
    {
      id: 'rest-2',
      name: 'Sushi Master',
      description: 'Authentic Japanese sushi and ramen, prepared by master chefs.',
      imageUrl: 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=400',
      coverImageUrl: 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=800',
      category: 'Japanese',
      rating: 4.8,
      reviewCount: 567,
      deliveryTimeMin: 25,
      deliveryTimeMax: 40,
      deliveryFee: 3.99,
      minimumOrder: 20.00,
      latitude: 37.7849,
      longitude: -122.4094,
      address: '456 Oak St, San Francisco, CA',
      isOpen: true,
      openingTime: '11:00',
      closingTime: '23:00',
    },
    {
      id: 'rest-3',
      name: 'Burger Joint',
      description: 'Juicy burgers and crispy fries made with premium ingredients.',
      imageUrl: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400',
      coverImageUrl: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800',
      category: 'Burgers',
      rating: 4.3,
      reviewCount: 189,
      deliveryTimeMin: 15,
      deliveryTimeMax: 25,
      deliveryFee: 0,
      minimumOrder: 10.00,
      latitude: 37.7649,
      longitude: -122.4294,
      address: '789 Pine St, San Francisco, CA',
      isOpen: true,
      openingTime: '10:00',
      closingTime: '00:00',
    },
    {
      id: 'rest-4',
      name: 'Taco Fiesta',
      description: 'Authentic Mexican tacos, burritos, and quesadillas.',
      imageUrl: 'https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=400',
      category: 'Mexican',
      rating: 4.4,
      reviewCount: 312,
      deliveryTimeMin: 20,
      deliveryTimeMax: 30,
      deliveryFee: 1.99,
      minimumOrder: 12.00,
      latitude: 37.7549,
      longitude: -122.4394,
      address: '321 Elm St, San Francisco, CA',
      isOpen: true,
      openingTime: '09:00',
      closingTime: '22:00',
    },
  ];

  for (const restaurant of restaurants) {
    await prisma.restaurant.upsert({
      where: { id: restaurant.id },
      update: {},
      create: restaurant,
    });
  }

  console.log('Created restaurants:', restaurants.length);

  // Create menu items for Pizza Palace
  const pizzaMenuItems = [
    {
      id: 'menu-1',
      restaurantId: 'rest-1',
      name: 'Margherita Pizza',
      description: 'Fresh tomatoes, mozzarella cheese, basil, and olive oil',
      price: 14.99,
      imageUrl: 'https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=400',
      category: 'Pizza',
      isAvailable: true,
      isPopular: true,
    },
    {
      id: 'menu-2',
      restaurantId: 'rest-1',
      name: 'Pepperoni Pizza',
      description: 'Classic pepperoni with mozzarella cheese',
      price: 16.99,
      imageUrl: 'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=400',
      category: 'Pizza',
      isAvailable: true,
      isPopular: true,
    },
    {
      id: 'menu-3',
      restaurantId: 'rest-1',
      name: 'Caesar Salad',
      description: 'Crisp romaine lettuce with parmesan and croutons',
      price: 9.99,
      imageUrl: null,
      category: 'Salads',
      isAvailable: true,
      isPopular: false,
    },
    {
      id: 'menu-4',
      restaurantId: 'rest-1',
      name: 'Garlic Bread',
      description: 'Toasted bread with garlic butter and herbs',
      price: 5.99,
      imageUrl: null,
      category: 'Sides',
      isAvailable: true,
      isPopular: false,
    },
  ];

  for (const item of pizzaMenuItems) {
    await prisma.menuItem.upsert({
      where: { id: item.id },
      update: {},
      create: item,
    });
  }

  // Create menu item options
  const sizeOption = await prisma.menuItemOption.upsert({
    where: { id: 'opt-size' },
    update: {},
    create: {
      id: 'opt-size',
      menuItemId: 'menu-1',
      name: 'Size',
      type: 'single',
      required: true,
    },
  });

  await prisma.menuItemOptionChoice.createMany({
    data: [
      { id: 'choice-small', optionId: sizeOption.id, name: 'Small (10")', price: 0 },
      { id: 'choice-medium', optionId: sizeOption.id, name: 'Medium (12")', price: 3 },
      { id: 'choice-large', optionId: sizeOption.id, name: 'Large (14")', price: 5 },
    ],
    skipDuplicates: true,
  });

  const toppingsOption = await prisma.menuItemOption.upsert({
    where: { id: 'opt-toppings' },
    update: {},
    create: {
      id: 'opt-toppings',
      menuItemId: 'menu-1',
      name: 'Extra Toppings',
      type: 'multiple',
      required: false,
      maxSelect: 5,
    },
  });

  await prisma.menuItemOptionChoice.createMany({
    data: [
      { id: 'choice-pepperoni', optionId: toppingsOption.id, name: 'Pepperoni', price: 1.50 },
      { id: 'choice-mushrooms', optionId: toppingsOption.id, name: 'Mushrooms', price: 1 },
      { id: 'choice-olives', optionId: toppingsOption.id, name: 'Olives', price: 1 },
      { id: 'choice-bacon', optionId: toppingsOption.id, name: 'Bacon', price: 2 },
    ],
    skipDuplicates: true,
  });

  console.log('Created menu items and options');

  // Create a test driver
  await prisma.driver.upsert({
    where: { id: 'driver-1' },
    update: {},
    create: {
      id: 'driver-1',
      name: 'Mike Johnson',
      phone: '+15559876543',
      vehicleType: 'Car',
      isAvailable: true,
      rating: 4.9,
    },
  });

  console.log('Created test driver');
  console.log('Seeding completed!');
}

main()
  .catch((e) => {
    console.error('Seeding error:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
