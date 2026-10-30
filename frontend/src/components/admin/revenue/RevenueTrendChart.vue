<template>
  <div class="trend">
    <div class="trend-legend">
      <span v-for="item in series" :key="item.key" class="trend-legend-item">
        <span class="trend-swatch" :style="{ backgroundColor: item.color }"></span>
        {{ item.label }}
      </span>
    </div>

    <div class="trend-plot">
      <div v-for="tick in ticks" :key="tick" class="trend-grid" :style="{ bottom: `${(tick / axisMax) * 100}%` }">
        <span class="trend-tick">{{ formatTick(tick) }}</span>
      </div>

      <div class="trend-columns">
        <div
          v-for="(period, index) in periods"
          :key="period.key"
          class="trend-column"
          tabindex="0"
          :aria-label="describe(period)"
          @pointerenter="activeKey = period.key"
          @pointerleave="activeKey = null"
          @focus="activeKey = period.key"
          @blur="activeKey = null"
        >
          <div class="trend-stack" :style="{ height: `${(period.total / axisMax) * 100}%` }">
            <span v-if="period.key === peakKey" class="trend-peak">{{ formatEuros(period.total) }}</span>
            <div class="trend-stack-fill">
              <div
                v-for="segment in period.segments"
                :key="segment.key"
                class="trend-segment"
                :style="{ flexGrow: segment.value, backgroundColor: segment.color }"
              ></div>
            </div>
          </div>

          <div
            v-if="activeKey === period.key"
            class="trend-tooltip"
            :class="{ 'trend-tooltip--start': index < 2, 'trend-tooltip--end': index > periods.length - 3 }"
          >
            <div class="trend-tooltip-title">{{ period.title }}</div>
            <div v-for="item in series" :key="item.key" class="trend-tooltip-row">
              <span class="trend-tooltip-key" :style="{ backgroundColor: item.color }"></span>
              <strong>{{ formatEuros(period.values[item.key], { cents: true }) }}</strong>
              <span>{{ item.label }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="trend-labels">
      <span v-for="period in periods" :key="period.key" class="trend-label">{{ period.label }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { formatEuros } from '@/utils/revenue.js';

const props = defineProps({
  // [{ key, label, title, values: { [seriesKey]: number } }]
  data: { type: Array, required: true },
  // [{ key, label, color }], bottom of the stack first
  series: { type: Array, required: true },
});

const activeKey = ref(null);

const periods = computed(() => props.data.map(period => {
  const segments = props.series
    .map(item => ({ key: item.key, color: item.color, value: period.values[item.key] }))
    .filter(segment => segment.value > 0);
  return { ...period, segments, total: segments.reduce((sum, s) => sum + s.value, 0) };
}));

const peakTotal = computed(() => Math.max(...periods.value.map(p => p.total), 0));
const peakKey = computed(() => periods.value.find(p => p.total === peakTotal.value && p.total > 0)?.key);

// A round top for the axis, with headroom for the label on the tallest column.
const axisMax = computed(() => {
  const target = peakTotal.value * 1.12;
  if (target <= 0) return 100;
  const magnitude = 10 ** Math.floor(Math.log10(target));
  const step = [1, 2, 2.5, 5, 10].find(candidate => candidate * magnitude >= target);
  return step * magnitude;
});

const ticks = computed(() => [0, 1, 2, 3, 4].map(i => (axisMax.value / 4) * i));

function formatTick(value) {
  return value >= 1000 ? `€${value / 1000}K` : `€${value}`;
}

function describe(period) {
  const parts = props.series.map(item => `${item.label} ${formatEuros(period.values[item.key], { cents: true })}`);
  return `${period.title}: ${parts.join(', ')}`;
}
</script>

<style scoped>
.trend {
  --trend-axis-width: 44px;
  --trend-text: rgba(0, 0, 0, 0.87);
  --trend-muted: rgba(0, 0, 0, 0.6);
  --trend-grid: rgba(0, 0, 0, 0.1);
}

.trend-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin-bottom: 20px;
  font-size: 0.75rem;
  color: var(--trend-muted);
}

.trend-legend-item {
  display: inline-flex;
  align-items: center;
}

.trend-swatch {
  width: 10px;
  height: 10px;
  margin-right: 6px;
  border-radius: 2px;
}

.trend-plot {
  position: relative;
  height: 240px;
  margin-left: var(--trend-axis-width);
}

.trend-grid {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px solid var(--trend-grid);
}

.trend-tick {
  position: absolute;
  right: 100%;
  margin-right: 8px;
  transform: translateY(-50%);
  font-size: 0.6875rem;
  color: var(--trend-muted);
  white-space: nowrap;
}

.trend-columns {
  position: absolute;
  inset: 0;
  display: flex;
}

.trend-column {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  outline: none;
  border-radius: 4px;
}

.trend-column:hover,
.trend-column:focus-visible {
  background-color: rgba(0, 0, 0, 0.04);
}

.trend-column:focus-visible {
  box-shadow: inset 0 0 0 2px rgba(19, 24, 46, 0.5);
}

.trend-stack {
  position: relative;
  width: 60%;
  max-width: 24px;
}

.trend-stack-fill {
  display: flex;
  flex-direction: column-reverse;
  gap: 2px;
  height: 100%;
  border-radius: 4px 4px 0 0;
  overflow: hidden;
}

.trend-segment {
  flex-basis: 2px;
  min-height: 2px;
}

.trend-peak {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 4px;
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--trend-text);
  white-space: nowrap;
}

.trend-tooltip {
  position: absolute;
  bottom: calc(100% - 28px);
  left: 50%;
  z-index: 2;
  transform: translateX(-50%);
  min-width: 190px;
  padding: 8px 12px;
  border-radius: 6px;
  background-color: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  font-size: 0.75rem;
  color: var(--trend-muted);
  pointer-events: none;
}

.trend-tooltip--start {
  left: 0;
  transform: none;
}

.trend-tooltip--end {
  left: auto;
  right: 0;
  transform: none;
}

.trend-tooltip-title {
  margin-bottom: 4px;
  font-weight: 600;
  color: var(--trend-text);
}

.trend-tooltip-row {
  display: flex;
  align-items: center;
  gap: 6px;
  line-height: 1.6;
  white-space: nowrap;
}

.trend-tooltip-row strong {
  color: var(--trend-text);
}

.trend-tooltip-key {
  flex: none;
  width: 10px;
  height: 2px;
}

.trend-labels {
  display: flex;
  margin-top: 6px;
  margin-left: var(--trend-axis-width);
}

.trend-label {
  flex: 1 1 0;
  min-width: 0;
  overflow: hidden;
  text-align: center;
  font-size: 0.6875rem;
  color: var(--trend-muted);
}
</style>
