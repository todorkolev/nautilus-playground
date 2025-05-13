<template>
  <div class="strategy-card">
    <div class="strategy-header">
      <h3>{{ name }}</h3>
    </div>
    <div class="strategy-content">
      <p>{{ description }}</p>
      <div class="strategy-features">
        <h4>Features:</h4>
        <ul>
          <li v-for="feature in features" :key="feature">{{ feature }}</li>
        </ul>
      </div>
      <div v-if="code" class="strategy-code">
        <pre><code>{{ code }}</code></pre>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  name: {
    type: String,
    required: true
  },
  description: {
    type: String,
    required: true
  },
  features: {
    type: Array,
    default: () => []
  },
  code: {
    type: String,
    default: ''
  }
})
</script>

<style>
.strategy-card {
  background-color: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 1rem;
}

.strategy-header {
  background-color: var(--primary-color, #5d8392);
  color: white;
  padding: 0.75rem 1rem;
}

.strategy-header h3 {
  margin: 0;
  color: white;
}

.strategy-content {
  padding: 1rem;
}

.strategy-features {
  margin-top: 0.5rem;
}

.strategy-features h4 {
  margin-bottom: 0.5rem;
}

.strategy-features ul {
  margin: 0;
  padding-left: 1.5rem;
}

.strategy-code {
  margin-top: 1rem;
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 0.5rem;
  overflow: auto;
}

.strategy-code pre {
  margin: 0;
}
</style>
