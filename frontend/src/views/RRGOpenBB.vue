<template>
  <div class="rrg-view">
    <div class="rrg-header">
      <h1>Relative Rotation Graph &mdash; OpenBB</h1>
      <p class="rrg-method">
        OpenBB-style &middot; daily closes, weekly tail spacing &middot; full-sample z-score &middot;
        RS-Momentum = ln(1+r<sub>252</sub>) &minus; ln(1+r<sub>21</sub>) &middot; centred on 0
      </p>
      <p class="rrg-caveat">
        The full-sample z-score normalises every point using the whole history,
        including data recorded after it. Fine for reading today's picture, not
        safe to backtest on.
      </p>
    </div>

    <RrgChart
      endpoint="/api/rrg-openbb-data"
      :center="0"
      tail-description="Daily data, weekly tail spacing,"
    />
  </div>
</template>

<script>
import RrgChart from '../components/RrgChart.vue';

export default {
  name: 'RRGOpenBB',
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

.rrg-caveat {
  color: #9a7b00;
  font-size: 12px;
  margin-top: 6px;
}
</style>
