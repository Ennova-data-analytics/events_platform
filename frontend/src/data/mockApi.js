// This file simulates a basic API by exporting arrays of mock data.
export const mockEvents = [
    {
      id: 1,
      name: 'Annual Tech Summit 2025',
      date: '2025-10-22T18:00:00Z',
      location: 'ESADE Sant Cugat Campus',
      description: 'Join us for the biggest tech event of the year, featuring talks from industry leaders on AI, blockchain, and the future of technology. Networking opportunities and catering provided.',
      imageUrl: 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?auto=format&fit=crop&q=80&w=2070',
      price: 15.00,
      capacity: 100,
    },
    {
      id: 2,
      name: 'Marketing & Branding Workshop',
      date: '2025-11-05T17:30:00Z',
      location: 'Online via Zoom',
      description: 'A hands-on workshop designed to help you build a powerful brand identity. Learn the fundamentals of digital marketing from an expert in the field.',
      imageUrl: 'https://images.unsplash.com/photo-1556740738-b6a63e27c4df?auto=format&fit=crop&q=80&w=2070',
      price: 5.00,
      capacity: 50,
    },
    {
      id: 3,
      name: 'Startup Pitch Night',
      date: '2025-11-18T19:00:00Z',
      location: 'ESADE Pedralbes, Fusion Point',
      description: 'Watch the brightest ESADE startups pitch their ideas to a panel of venture capitalists. An exciting evening of innovation and networking.',
      imageUrl: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&q=80&w=2071',
      price: 0.00, 
      capacity: 80,
    },
    {
        id: 4,
        name: 'Consulting Case Competition',
        date: '2025-11-29T09:00:00Z',
        location: 'ESADE Pedralbes, Room E101',
        description: 'Test your problem-solving skills in our annual case competition. Compete in teams to solve a real-world business challenge and present your solution to a panel of judges from top consulting firms.',
        imageUrl: 'https://images.unsplash.com/photo-1517048676732-d65bc937f952?auto=format&fit=crop&q=80&w=2070',
        price: 10.00,
        capacity: 60, 
    },
    {
        id: 5,
        name: 'End of Term Social Mixer',
        date: '2025-12-12T20:00:00Z',
        location: 'Local Bar Downtown',
        description: 'Celebrate the end of a successful term with us! A great opportunity to relax, network with fellow students and faculty in a casual setting. First drink is on us!',
        imageUrl: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&q=80&w=2071',
        price: 8.00,
        capacity: 120,
    },
    {
        id: 6,
        name: 'Intro to Python for Data Science Bootcamp',
        date: '2026-01-25T10:00:00Z',
        location: 'ESADE Sant Cugat, Tech Lab 3',
        description: 'A full-day, hands-on bootcamp for beginners. Learn the fundamentals of Python, Pandas, and Matplotlib for data analysis and visualization. No prior coding experience required. Laptop is mandatory.',
        imageUrl: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&q=80&w=2071',
        price: 25.00,
        capacity: 30,
    },
  ];


export const mockUserAttendedEvents = [
  {
    id: 2,
    name: 'Marketing & Branding Workshop',
    date: '2025-11-05T17:30:00Z',
    feedbackSubmitted: true,
    presentationUrl: '/mock-assets/marketing-presentation.pdf', 
    certificateUrl: '/mock-assets/marketing-certificate.pdf', 
  },
  {
    id: 5,
    name: 'End of Term Social Mixer',
    date: '2025-12-12T20:00:00Z',
    feedbackSubmitted: false,
    presentationUrl: null,
    certificateUrl: null,
  },
  
  
]