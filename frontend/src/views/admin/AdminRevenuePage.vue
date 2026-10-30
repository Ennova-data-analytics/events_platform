<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-4 flex-wrap ga-2">
      <h1 :class="$vuetify.display.mobile ? 'text-h6' : 'text-h5'">Revenue</h1>
      <div class="d-flex align-center flex-wrap ga-2">
        <v-select
          v-model="fiscalYear"
          :items="overview?.available_years || []"
          item-title="label"
          item-value="fiscal_year"
          aria-label="Fiscal year"
          variant="outlined"
          density="compact"
          hide-details
          style="min-width: 130px"
          @update:model-value="load"
        />
        <v-btn variant="tonal" prepend-icon="mdi-download" :disabled="!overview?.events.length" @click="exportReport">
          Export report
        </v-btn>
      </div>
    </div>

    <v-alert v-if="loadError" type="error" variant="tonal" class="mb-4">
      {{ loadError }}
      <template #append>
        <v-btn variant="text" size="small" @click="load">Retry</v-btn>
      </template>
    </v-alert>

    <div v-if="isLoading && !overview" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
    </div>

    <template v-else-if="overview">
      <!-- KPI tiles -->
      <v-row class="mb-1" dense>
        <v-col v-for="kpi in kpis" :key="kpi.label" cols="6" md="3">
          <v-card variant="tonal" :color="kpi.color" class="fill-height">
            <v-card-text class="py-4">
              <div class="d-flex align-center mb-1">
                <v-icon :icon="kpi.icon" size="small" class="mr-2" />
                <span class="text-caption">{{ kpi.label }}</span>
              </div>
              <div class="text-h5 font-weight-bold">{{ kpi.value }}</div>
              <div class="text-caption text-medium-emphasis">{{ kpi.sub }}</div>
              <div v-if="kpi.change" class="text-caption d-flex align-center mt-1">
                <v-icon v-if="kpi.change.icon" :icon="kpi.change.icon" size="x-small" class="mr-1" />
                {{ kpi.change.text }}
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row class="mt-1">
        <!-- Trend -->
        <v-col cols="12" md="8">
          <v-card class="fill-height">
            <v-card-title class="d-flex justify-space-between align-center flex-wrap ga-2">
              <span class="text-subtitle-1 font-weight-bold">Revenue over the year</span>
              <div class="d-flex flex-wrap ga-2">
                <v-btn-toggle v-model="granularity" mandatory density="compact" variant="outlined" divided>
                  <v-btn value="monthly" size="small">Monthly</v-btn>
                  <v-btn value="quarterly" size="small">Quarterly</v-btn>
                </v-btn-toggle>
                <v-btn-toggle v-model="trendView" mandatory density="compact" variant="outlined" divided>
                  <v-btn value="chart" size="small" icon="mdi-chart-bar" aria-label="Show as chart"></v-btn>
                  <v-btn value="table" size="small" icon="mdi-table" aria-label="Show as table"></v-btn>
                </v-btn-toggle>
              </div>
            </v-card-title>
            <v-card-text>
              <RevenueTrendChart v-if="trendView === 'chart'" :data="periods" :series="REVENUE_SERIES" />
              <v-table v-else density="compact">
                <thead>
                  <tr>
                    <th>Period</th>
                    <th v-for="item in REVENUE_SERIES" :key="item.key" class="text-right">{{ item.label }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="period in periods" :key="period.key">
                    <td>{{ period.title }}</td>
                    <td v-for="item in REVENUE_SERIES" :key="item.key" class="text-right">
                      {{ formatEuros(period.values[item.key], { cents: true }) }}
                    </td>
                  </tr>
                </tbody>
              </v-table>
              <div class="text-caption text-medium-emphasis mt-3">
                Income is shown in the month of the event, not the month it was paid.
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Sources -->
        <v-col cols="12" md="4">
          <v-card class="fill-height">
            <v-card-title class="text-subtitle-1 font-weight-bold">Where the money comes from</v-card-title>
            <v-card-text>
              <div class="text-h5 font-weight-bold">{{ formatEuros(overview.totals.total_collected) }}</div>
              <div class="text-caption text-medium-emphasis mb-4">Collected in {{ overview.label }}</div>
              <RevenueShareBar :segments="sourceSegments" class="mb-4" />
              <div v-for="source in sourceSegments" :key="source.key" class="d-flex align-center py-1 text-body-2">
                <span class="source-key mr-2" :style="{ backgroundColor: source.color }"></span>
                <span>{{ source.label }}</span>
                <v-spacer />
                <span class="font-weight-medium">{{ formatEuros(source.value) }}</span>
                <span class="text-caption text-medium-emphasis source-share">{{ sharePercent(source.value) }}</span>
              </div>
              <v-divider class="my-3" />
              <div class="d-flex text-body-2 py-1">
                <span>Discounts given</span>
                <v-spacer />
                <span class="font-weight-medium">{{ formatEuros(overview.totals.discounts_given) }}</span>
              </div>
              <div class="d-flex text-body-2 py-1">
                <span>Approved, not yet paid</span>
                <v-spacer />
                <span class="font-weight-medium">{{ formatEuros(overview.totals.awaiting_payment) }}</span>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-alert v-if="overview.summer.event_count" type="info" variant="tonal" density="compact" class="mt-4">
        {{ formatEuros(overview.summer.total_collected) }} from {{ overview.summer.event_count }}
        event{{ overview.summer.event_count === 1 ? '' : 's' }} held in the following July and August
        {{ overview.summer.event_count === 1 ? 'is' : 'are' }} not included: {{ overview.label }} ends in June.
      </v-alert>

      <!-- Year on year -->
      <v-card class="mt-4">
        <v-card-title class="text-subtitle-1 font-weight-bold">{{ overview.previous_label }} → {{ overview.label }}</v-card-title>
        <v-card-subtitle v-if="overview.comparison.in_progress" class="text-wrap">
          {{ overview.label }} is still running, so both years count only events held up to {{ comparedUpTo }}.
        </v-card-subtitle>
        <v-card-text>
          <v-table density="compact">
            <thead>
              <tr>
                <th></th>
                <th class="text-right">{{ overview.previous_label }}</th>
                <th class="text-right">{{ overview.label }}</th>
                <th class="text-right">Change</th>
                <th class="text-right">Variance</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in comparisonRows" :key="row.label">
                <td>{{ row.label }}</td>
                <td class="text-right">{{ row.format(row.previous) }}</td>
                <td class="text-right">{{ row.format(row.current) }}</td>
                <td class="text-right">{{ signed(row.current - row.previous, row.format) }}</td>
                <td class="text-right">{{ variance(row.current, row.previous) }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-card-text>
      </v-card>

      <!-- By event -->
      <v-card class="mt-4">
        <v-card-title class="text-subtitle-1 font-weight-bold">By event</v-card-title>
        <v-data-table
          :headers="eventHeaders"
          :items="eventRows"
          item-value="event_id"
          :loading="isLoading"
          :sort-by="[{ key: 'total_collected', order: 'desc' }]"
          no-data-text="No ticket sales or donations in this year"
        >
          <template #[`item.event_name`]="{ item }">
            <router-link :to="`/admin/events/view/${item.event_id}`" class="event-link">{{ item.event_name }}</router-link>
            <v-chip v-if="item.is_charitable" size="x-small" variant="tonal" color="pink-darken-1" class="ml-2">Charity</v-chip>
          </template>
          <template #[`item.total_collected`]="{ item }">
            <div class="d-flex align-center ga-2">
              <span class="collected-value">{{ formatEuros(item.total_collected) }}</span>
              <RevenueShareBar :segments="eventSegments(item)" :scale="largestEvent" :height="8" />
            </div>
          </template>
        </v-data-table>
      </v-card>

      <div class="text-caption text-medium-emphasis mt-3">
        Tickets on charity events and all donations go to the charity, so they are not part of ticket revenue.
        Amounts are before Stripe fees, which the platform doesn't record. Cancelled events and cancelled
        registrations are left out, on the assumption they were refunded.
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { AdminService } from '@/services/AdminService.js';
import RevenueShareBar from '@/components/admin/revenue/RevenueShareBar.vue';
import RevenueTrendChart from '@/components/admin/revenue/RevenueTrendChart.vue';
import { downloadCsv } from '@/utils/csv.js';
import { REVENUE_SERIES, formatEuros } from '@/utils/revenue.js';

const overview = ref(null);
const fiscalYear = ref(null);
const isLoading = ref(false);
const loadError = ref('');
const granularity = ref('monthly');
const trendView = ref('chart');

const formatCount = value => Number(value).toLocaleString('en-IE');
const formatMoney = value => formatEuros(value, { cents: true });

const numberOfTickets = totals => totals.paid_tickets + totals.free_tickets;

function monthDate(key) {
  const [year, month] = key.split('-').map(Number);
  return new Date(year, month - 1, 1);
}

const monthlyPeriods = computed(() => overview.value.months.map(month => {
  const date = monthDate(month.month);
  return {
    key: month.month,
    // en-US, because en-GB shortens September to "Sept" and breaks the axis rhythm.
    label: date.toLocaleString('en-US', { month: 'short' }),
    title: date.toLocaleString('en-GB', { month: 'long', year: 'numeric' }),
    values: Object.fromEntries(REVENUE_SERIES.map(item => [item.key, Number(month[item.key])])),
  };
}));

// The fiscal year is ten months long, so the last quarter is June on its own.
const quarterlyPeriods = computed(() => {
  const quarters = [];
  for (let i = 0; i < monthlyPeriods.value.length; i += 3) {
    const months = monthlyPeriods.value.slice(i, i + 3);
    const number = i / 3 + 1;
    const span = months.length > 1 ? `${months[0].label}–${months.at(-1).label}` : months[0].label;
    quarters.push({
      key: `Q${number}`,
      label: `Q${number}`,
      title: `Q${number} (${span})`,
      values: Object.fromEntries(REVENUE_SERIES.map(item => [
        item.key,
        months.reduce((sum, month) => sum + month.values[item.key], 0),
      ])),
    });
  }
  return quarters;
});

const periods = computed(() => (granularity.value === 'monthly' ? monthlyPeriods.value : quarterlyPeriods.value));

const sourceSegments = computed(() => REVENUE_SERIES.map(item => ({
  ...item,
  value: Number(overview.value.totals[item.key]),
})));

function sharePercent(value) {
  const total = Number(overview.value.totals.total_collected);
  return total > 0 ? `${Math.round((value / total) * 100)}%` : '—';
}

const comparedUpTo = computed(() => new Date(overview.value.comparison.as_of)
  .toLocaleDateString('en-GB', { day: 'numeric', month: 'long' }));

function changeFrom(current, previous) {
  if (!overview.value) return null;
  const year = overview.value.previous_label;
  const scope = overview.value.comparison.in_progress ? `same point in ${year}` : year;
  if (previous === 0) return { text: current > 0 ? `New vs ${scope}` : `Flat vs ${scope}` };
  const percent = ((current - previous) / Math.abs(previous)) * 100;
  return {
    icon: percent > 0 ? 'mdi-arrow-up' : percent < 0 ? 'mdi-arrow-down' : null,
    text: `${Math.abs(percent).toFixed(1)}% vs ${scope}`,
  };
}

const compared = computed(() => overview.value.comparison);

function comparisonOf(figure) {
  const read = totals => (typeof figure === 'function' ? figure(totals) : Number(totals[figure]));
  return { current: read(compared.value.current), previous: read(compared.value.previous) };
}

const kpis = computed(() => {
  const totals = overview.value.totals;
  const change = figure => {
    const { current, previous } = comparisonOf(figure);
    return changeFrom(current, previous);
  };
  return [
    {
      label: 'Ticket revenue',
      value: formatEuros(totals.ticket_revenue),
      sub: `${formatCount(totals.event_count)} event${totals.event_count === 1 ? '' : 's'}`,
      icon: 'mdi-ticket-confirmation',
      color: 'blue-darken-2',
      change: change('ticket_revenue'),
    },
    {
      label: 'Net of commissions',
      value: formatEuros(totals.net_revenue),
      sub: `${formatEuros(totals.commission_owed)} owed to referrers`,
      icon: 'mdi-cash-check',
      color: 'green-darken-2',
      change: change('net_revenue'),
    },
    {
      label: 'Raised for charity',
      value: formatEuros(totals.raised_for_charity),
      sub: 'Tickets and donations',
      icon: 'mdi-hand-heart',
      color: 'pink-darken-1',
      change: change('raised_for_charity'),
    },
    {
      label: 'Tickets',
      value: formatCount(numberOfTickets(totals)),
      sub: `${formatCount(totals.paid_tickets)} paid · ${formatCount(totals.free_tickets)} free`,
      icon: 'mdi-account-multiple',
      color: 'deep-purple-darken-1',
      change: change(numberOfTickets),
    },
  ];
});

const comparisonRows = computed(() => [
  { label: 'Ticket revenue', format: formatMoney, ...comparisonOf('ticket_revenue') },
  { label: 'Referral commissions', format: formatMoney, ...comparisonOf('commission_owed') },
  { label: 'Net of commissions', format: formatMoney, ...comparisonOf('net_revenue') },
  { label: 'Raised for charity', format: formatMoney, ...comparisonOf('raised_for_charity') },
  { label: 'Tickets', format: formatCount, ...comparisonOf(numberOfTickets) },
  { label: 'Events', format: formatCount, ...comparisonOf('event_count') },
]);

function signed(value, format) {
  if (value === 0) return format(0);
  return `${value > 0 ? '+' : '−'}${format(Math.abs(value))}`;
}

function variance(current, previous) {
  if (previous === 0) return '—';
  const percent = ((current - previous) / Math.abs(previous)) * 100;
  return `${percent > 0 ? '+' : percent < 0 ? '−' : ''}${Math.abs(percent).toFixed(1)}%`;
}

const eventHeaders = [
  { title: 'Event', key: 'event_name' },
  { title: 'Date', key: 'event_date_start', value: item => new Date(item.event_date_start).toLocaleDateString('en-GB') },
  { title: 'Paid', key: 'paid_tickets', align: 'end' },
  { title: 'Free', key: 'free_tickets', align: 'end' },
  { title: 'Ticket revenue', key: 'ticket_revenue', align: 'end', value: item => formatMoney(item.ticket_revenue), sortRaw: (a, b) => a.ticket_revenue - b.ticket_revenue },
  { title: 'For charity', key: 'raised_for_charity', align: 'end', value: item => formatMoney(item.raised_for_charity), sortRaw: (a, b) => a.raised_for_charity - b.raised_for_charity },
  { title: 'Commission', key: 'commission_owed', align: 'end', value: item => formatMoney(item.commission_owed), sortRaw: (a, b) => a.commission_owed - b.commission_owed },
  { title: 'Net', key: 'net_revenue', align: 'end', value: item => formatMoney(item.net_revenue), sortRaw: (a, b) => a.net_revenue - b.net_revenue },
  { title: 'Collected', key: 'total_collected', sortRaw: (a, b) => a.total_collected - b.total_collected, minWidth: '180px' },
];

const MONEY_COLUMNS = [
  'ticket_revenue', 'charity_ticket_revenue', 'donations', 'raised_for_charity',
  'total_collected', 'commission_owed', 'net_revenue', 'awaiting_payment', 'discounts_given',
];

const eventRows = computed(() => overview.value.events.map(event => ({
  ...event,
  ...Object.fromEntries(MONEY_COLUMNS.map(key => [key, Number(event[key])])),
})));

const largestEvent = computed(() => Math.max(...eventRows.value.map(event => event.total_collected), 0));

function eventSegments(event) {
  return REVENUE_SERIES.map(item => ({ key: item.key, color: item.color, value: event[item.key] }));
}

function exportReport() {
  const { label, totals } = overview.value;
  downloadCsv(`revenue-${label.replace('/', '-')}.csv`, [
    ['Event', 'Date', 'Charity', 'Paid tickets', 'Free tickets', 'Ticket revenue', 'Charity tickets', 'Donations',
      'Commission owed', 'Net of commissions', 'Total collected', 'Discounts given', 'Approved not yet paid'],
    ...eventRows.value.map(event => [
      event.event_name,
      new Date(event.event_date_start).toLocaleDateString('en-GB'),
      event.is_charitable ? (event.charity_name || 'Yes') : '',
      event.paid_tickets,
      event.free_tickets,
      event.ticket_revenue,
      event.charity_ticket_revenue,
      event.donations,
      event.commission_owed,
      event.net_revenue,
      event.total_collected,
      event.discounts_given,
      event.awaiting_payment,
    ]),
    [
      `Total ${label}`, '', '', totals.paid_tickets, totals.free_tickets,
      ...['ticket_revenue', 'charity_ticket_revenue', 'donations', 'commission_owed', 'net_revenue',
        'total_collected', 'discounts_given', 'awaiting_payment'].map(key => Number(totals[key])),
    ],
  ]);
}

async function load() {
  isLoading.value = true;
  loadError.value = '';
  try {
    const response = await AdminService.getRevenueOverview(fiscalYear.value);
    overview.value = response.data;
    fiscalYear.value = response.data.fiscal_year;
  } catch (error) {
    console.error('Failed to load revenue:', error);
    loadError.value = error.response?.data?.detail || 'Could not load revenue. Please try again.';
  } finally {
    isLoading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.source-key {
  flex: none;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.source-share {
  width: 40px;
  text-align: right;
}

.collected-value {
  min-width: 56px;
}

.event-link {
  color: inherit;
  font-weight: 500;
}
</style>
