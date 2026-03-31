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
    path: '/event/:id/register',
    name: 'event-register',
    component: () => import('../views/EventRegistrationPage.vue')
  },
  {
    path: '/event/:id/registered',
    name: 'event-registered',
    component: () => import('../views/EventRegistrationConfirmationPage.vue')
  },
  {
    path: '/event/:id/claim-invite',
    name: 'claim-team-invite',
    component: () => import('../views/ClaimTeamInvitePage.vue')
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
    name: 'public-feedback',
    component: () => import('../views/PublicFeedbackFormPage.vue')
  },
  {
    // Public ticket view — works for both guest tokens and registered-user shared links
    path: '/ticket/:token',
    name: 'ticket-view',
    component: () => import('../views/TicketViewPage.vue')
  },
  {
    // Authenticated user's own ticket for a specific registration
    path: '/event/:id/ticket/:registrationId',
    name: 'my-ticket',
    component: () => import('../views/MyTicketPage.vue'),
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
      },
      {
        path: 'feedback-templates',
        name: 'admin-feedback-templates',
        component: () => import('../views/admin/AdminFeedbackTemplatesListPage.vue')
      },
      {
        path: 'feedback-templates/create',
        name: 'admin-feedback-template-create',
        component: () => import('../views/admin/AdminFeedbackTemplateEditPage.vue')
      },
      {
        path: 'feedback-templates/edit/:id',
        name: 'admin-feedback-template-edit',
        component: () => import('../views/admin/AdminFeedbackTemplateEditPage.vue')
      },
      {
        path: 'events/:id/feedback',
        name: 'admin-event-feedback',
        component: () => import('../views/admin/AdminEventFeedbackPage.vue')
      },
      {
        path: 'events/:id/scanner',
        name: 'admin-event-scanner',
        component: () => import('../views/admin/AdminScannerPage.vue')
      },
      {
        path: 'tutorials',
        name: 'admin-tutorials',
        component: () => import('../views/TutorialPage.vue')
      },
      {
        path: 'ennova-members',
        name: 'admin-ennova-members',
        component: () => import('../views/admin/AdminEnnovaMembersPage.vue')
      },
      {
        path: 'ai-documents',
        name: 'admin-ai-documents',
        component: () => import('../views/admin/AdminAIDocumentsPage.vue')
      },
      {
        path: 'user-roles',
        name: 'admin-user-roles',
        component: () => import('../views/admin/AdminUserRolesPage.vue'),
        meta: { requiresSuperAdmin: true }
      }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: routes
});

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore();
  const requiresAuth = to.meta.requiresAuth;

  if (requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } });
  } else if (to.meta.requiresSuperAdmin && !authStore.isSuperAdmin) {
    next({ name: 'admin-dashboard' });
  } else {
    next();
  }

});

export default router;