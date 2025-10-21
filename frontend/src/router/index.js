import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth.store';

const routes = [
  {
    path: '/',
    name: 'home',
    
    component: () => import('../views/HomePage.vue')
  },
  {

    path: '/event/:id',
    name: 'event-details',
    component: () => import('../views/EventDetailsPage.vue')
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginPage.vue')
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/RegistrationPage.vue')
  },
  {
   
    path: '/profile',
    name: 'profile',
    component: () => import('../views/ProfilePage.vue'),
    meta: { requiresAuth: true }
  },
  {
   
    path: '/profile/edit',
    name: 'profile-edit',
    component: () => import('../views/EditProfilePage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/forgot-password',
    name: 'forgot-password',
    component: () => import('../views/ForgotPasswordPage.vue')
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: () => import('../views/ResetPasswordPage.vue')
  },
  {
    path: '/feedback/:id',
    name: 'feedback',
    component: () => import('../views/FeedbackPage.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    component: () => import('../views/admin/AdminDashboard.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'admin-dashboard',
        component: () => import('../views/admin/AdminEventsListPage.vue') 
      },
      {
        path: 'events',
        name: 'admin-events',
        component: () => import('../views/admin/AdminEventsListPage.vue')
      },
      {
        path: 'events/create',
        name: 'admin-create-event',
        component: () => import('../views/admin/AdminCreateEventPage.vue')
      },
      {
        path: 'events/edit/:id', 
        name: 'admin-edit-event',
        component: () => import('../views/admin/AdminEditEventPage.vue')
      },
      {
        path: 'events/view/:id', 
        name: 'admin-view-event',
        component: () => import('../views/admin/AdminEventViewPage.vue')
      },
      {
        path: 'forms',
        name: 'admin-forms',
        component: () => import('../views/admin/AdminFormsListPage.vue')
      },
      {
        path: 'forms/create',
        name: 'admin-form-create',
        component: () => import('../views/admin/AdminFormEditPage.vue')
      },
      {
        path: 'forms/edit/:id',
        name: 'admin-form-edit',
        component: () => import('../views/admin/AdminFormEditPage.vue')
      },
      {
        path: 'email-templates',
        name: 'admin-email-templates',
        component: () => import('../views/admin/AdminEmailTemplatesListPage.vue')
      },
      {
        path: 'email-templates/create',
        name: 'admin-email-template-create',
        component: () => import('../views/admin/AdminEmailTemplateEditPage.vue')
      },
      {
        path: 'email-templates/edit/:id',
        name: 'admin-email-template-edit',
        component: () => import('../views/admin/AdminEmailTemplateEditPage.vue')
      }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: routes
});

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  const requiresAuth = to.meta.requiresAuth;

  if (requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login'});
  } else {
    next();
  }

});

export default router;