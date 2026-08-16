<template>
  <VueDatePicker
    v-model="model"
    :model-type="MODEL_FORMAT"
    :disabled="disabled"
    :readonly="readonly"
    :min-date="minDate || undefined"
    :max-date="maxDate || undefined"
    :start-date="startDate || undefined"
    :preset-dates="presetDates"
    :placeholder="placeholder"
    :locale="enGB"
    :week-start="1"
    :formats="{ input: DISPLAY_FORMAT }"
    :time-config="{
      is24: true,
      minutesIncrement: 5,
      minutesGridIncrement: 5,
      timePickerInline: true,
      startTime: defaultTime,
    }"
    :text-input="{
      format: TEXT_INPUT_FORMATS,
      applyOnBlur: true,
      enterSubmit: true,
      tabSubmit: true,
    }"
    :action-row="{
      showSelect: true,
      showCancel: true,
      showNow: true,
      showPreview: true,
      selectBtnLabel: 'Apply',
      nowBtnLabel: 'Now',
    }"
    :ui="{ menu: 'dtf-menu' }"
    teleport="body"
    :auto-apply="false"
  >
    <template
      #dp-input="{ value, onInput, onEnter, onTab, onBlur, onFocus, onKeypress, onPaste, onClear, openMenu, toggleMenu }"
    >
      <v-text-field
        :model-value="value"
        :label="label"
        :hint="hint"
        :persistent-hint="persistentHint"
        :variant="variant"
        :density="density"
        :disabled="disabled"
        :readonly="readonly"
        :placeholder="placeholder"
        :prepend-inner-icon="prependInnerIcon"
        :rules="wrappedRules"
        :hide-details="hideDetails"
        :clearable="clearable"
        autocomplete="off"
        @update:model-value="onInput"
        @keydown.enter="onEnter"
        @keydown.tab="onTab"
        @keypress="onKeypress"
        @paste="onPaste"
        @focus="onFocus"
        @blur="onBlur"
        @click="!(disabled || readonly) && openMenu()"
        @click:clear="onClear(); model = null"
      >
        <template #append-inner>
          <!-- `.stop` keeps this from also hitting the field's open-on-click. -->
          <v-icon
            icon="mdi-calendar-month-outline"
            :class="{ 'dtf-trigger--disabled': disabled || readonly }"
            class="dtf-trigger"
            @mousedown.prevent.stop
            @click.stop="!(disabled || readonly) && toggleMenu()"
          />
        </template>
      </v-text-field>
    </template>
  </VueDatePicker>
</template>

<script setup>
import { computed } from 'vue';
import { VueDatePicker } from '@vuepic/vue-datepicker';
import { addDays, addMonths, nextMonday, set, startOfDay } from 'date-fns';
import { enGB } from 'date-fns/locale';
import '@vuepic/vue-datepicker/dist/main.css';

// Matches the value shape of a native <input type="datetime-local">, so this
// component is a drop-in for the fields it replaced.
const MODEL_FORMAT = "yyyy-MM-dd'T'HH:mm";
const DISPLAY_FORMAT = 'dd/MM/yyyy HH:mm';
const TEXT_INPUT_FORMATS = [
  'dd/MM/yyyy HH:mm',
  'dd-MM-yyyy HH:mm',
  'yyyy-MM-dd HH:mm',
  'dd/MM/yyyy',
  'dd-MM-yyyy',
  'yyyy-MM-dd',
];

const props = defineProps({
  modelValue: { type: String, default: null },
  label: { type: String, default: '' },
  hint: { type: String, default: undefined },
  persistentHint: { type: Boolean, default: false },
  placeholder: { type: String, default: 'dd/mm/yyyy hh:mm' },
  variant: { type: String, default: 'outlined' },
  density: { type: String, default: 'default' },
  prependInnerIcon: { type: String, default: undefined },
  rules: { type: Array, default: () => [] },
  hideDetails: { type: [Boolean, String], default: false },
  clearable: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },
  minDate: { type: [String, Date], default: null },
  maxDate: { type: [String, Date], default: null },
  startDate: { type: [String, Date], default: null },
  // Time applied when a preset (or a bare date typed without a time) is picked.
  defaultTime: { type: Object, default: () => ({ hours: 9, minutes: 0 }) },
  // Pass an empty array to hide the shortcut sidebar.
  presets: {
    type: Array,
    default: () => ['today', 'tomorrow', 'nextMonday', 'inAWeek', 'inAMonth'],
  },
});

const emit = defineEmits(['update:modelValue']);

const model = computed({
  get: () => props.modelValue || null,
  set: (v) => emit('update:modelValue', v || null),
});

// Vuetify passes the *formatted* text to rules; callers write rules against the
// underlying datetime-local value, so evaluate them against that instead.
const wrappedRules = computed(() =>
  props.rules.map((rule) => () => rule(props.modelValue))
);

const PRESET_BUILDERS = {
  today: () => ({ label: 'Today', date: new Date() }),
  tomorrow: () => ({ label: 'Tomorrow', date: addDays(new Date(), 1) }),
  nextMonday: () => ({ label: 'Next Monday', date: nextMonday(new Date()) }),
  inAWeek: () => ({ label: 'In a week', date: addDays(new Date(), 7) }),
  inAMonth: () => ({ label: 'In a month', date: addMonths(new Date(), 1) }),
};

const presetDates = computed(() =>
  props.presets
    .map((key) => PRESET_BUILDERS[key]?.())
    .filter(Boolean)
    .map(({ label, date }) => ({
      label,
      value: set(startOfDay(date), {
        hours: props.defaultTime?.hours ?? 9,
        minutes: props.defaultTime?.minutes ?? 0,
      }),
    }))
);
</script>

<style>
/*
 * Unscoped on purpose: the picker menu is teleported to <body>.
 * The class is doubled so these win over the library's own `:root` defaults
 * regardless of stylesheet injection order (both would otherwise be 0-1-0).
 * Vuetify emits its theme variables on `:root` at runtime, so they resolve
 * outside `.v-application` too.
 */
.dp--theme-light.dp--theme-light,
.dp--theme-dark.dp--theme-dark {
  --dp-font-family: inherit;
  --dp-font-size: 0.875rem;
  --dp-border-radius: 8px;
  --dp-cell-border-radius: 8px;
  --dp-cell-size: 36px;
  --dp-cell-padding: 6px;
  --dp-menu-min-width: 290px;
  --dp-menu-padding: 8px 10px;
  --dp-row-margin: 3px 0;
  --dp-action-button-height: 32px;

  --dp-background-color: rgb(var(--v-theme-surface));
  --dp-text-color: rgba(var(--v-theme-on-surface), 0.87);
  --dp-primary-color: rgb(var(--v-theme-primary));
  --dp-primary-text-color: rgb(var(--v-theme-on-primary));
  --dp-primary-disabled-color: rgba(var(--v-theme-primary), 0.5);
  --dp-hover-color: rgba(var(--v-theme-on-surface), 0.08);
  --dp-hover-text-color: rgba(var(--v-theme-on-surface), 0.87);
  --dp-hover-icon-color: rgba(var(--v-theme-on-surface), 0.6);
  --dp-icon-color: rgba(var(--v-theme-on-surface), 0.6);
  --dp-secondary-color: rgba(var(--v-theme-on-surface), 0.38);
  --dp-border-color: rgba(var(--v-theme-on-surface), 0.16);
  --dp-menu-border-color: rgba(var(--v-theme-on-surface), 0.12);
  --dp-border-color-hover: rgba(var(--v-theme-on-surface), 0.38);
  --dp-border-color-focus: rgb(var(--v-theme-primary));
  --dp-disabled-color: rgba(var(--v-theme-on-surface), 0.04);
  --dp-disabled-color-text: rgba(var(--v-theme-on-surface), 0.26);
  --dp-danger-color: rgb(var(--v-theme-error));
  --dp-success-color: rgb(var(--v-theme-success));
  --dp-marker-color: rgb(var(--v-theme-error));
  --dp-highlight-color: rgba(var(--v-theme-primary), 0.12);
}

.dtf-menu {
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.12),
    0 12px 24px -4px rgba(0, 0, 0, 0.18);
}

.dtf-menu .dp--today {
  border: 1px solid rgb(var(--v-theme-primary));
}

.dtf-menu .dp--active,
.dtf-menu .dp--overlay-cell-active {
  font-weight: 600;
}

.dtf-menu .dp--calendar-header-item {
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

/* Preset shortcuts read as a quiet sidebar, not a stack of buttons. */
.dtf-menu .dp--preset-dates {
  border-right: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  padding: 8px 6px;
}

.dtf-menu .dp--preset-range {
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 0.8125rem;
  white-space: nowrap;
}

.dtf-menu .dp--action-buttons .dp--action-button {
  border-radius: 6px;
  padding: 0 14px;
  font-size: 0.8125rem;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.dtf-menu .dp--action-buttons .dp--action-select {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}

.dtf-trigger {
  cursor: pointer;
  opacity: 0.7;
}

.dtf-trigger:hover {
  opacity: 1;
}

.dtf-trigger--disabled {
  cursor: default;
  opacity: 0.4;
}
</style>
