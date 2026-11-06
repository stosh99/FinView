<template>
  <div class="rrg-view">
    <div class="rrg-header">
      <h1>Relative Rotation Graph</h1>
      <p class="rrg-method">
        JdK-style &middot; weekly closes &middot; rolling 52-week z-score &middot;
        RS-Momentum from the rate of change of RS-Ratio &middot; centred on 100
      </p>
    </div>

    <RrgChart endpoint="/api/rrg-data" :center="100" tail-description="Weekly tails" />
  </div>
</template>

<script>
import RrgChart from '../components/RrgChart.vue';

export default {
  name: 'RRG',
  components: { RrgChart }
};
</script>

<style scoped>
.rrg-view {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.rrg-header {
  text-align: center;
  margin-bottom: 16px;
}

h1 {
  color: #333;
  margin-bottom: 6px;
}

.rrg-method {
  color: #888;
  font-size: 13px;
}
</style>
