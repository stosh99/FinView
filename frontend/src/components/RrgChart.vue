<template>
  <div class="rrg-chart-wrapper">
    <p v-if="subtitle" class="rrg-subtitle">{{ subtitle }}</p>
    <div v-if="loading" class="rrg-state">Loading RRG data...</div>
    <div v-else-if="error" class="rrg-state error">{{ error }}</div>
    <div v-else ref="chartEl" class="rrg-chart"></div>
  </div>
</template>

<script>
import * as echarts from 'echarts';

const QUADRANT_COLORS = {
  leading: '#008217',
  weakening: '#9a7b00',
  lagging: '#d62728',
  improving: '#00749d'
};

export default {
  name: 'RrgChart',
  props: {
    // API path supplying { ticker, latest, tail } records.
    endpoint: {
      type: String,
      required: true
    },
    // Value the quadrants divide on. The JdK-style series centres on 100,
    // OpenBB's z-scored series centres on 0.
    center: {
      type: Number,
      default: 100
    },
    // Describes the tail spacing, e.g. "Weekly tails".
    tailDescription: {
      type: String,
      default: 'Weekly tails'
    }
  },
  data() {
    return {
      chart: null,
      loading: true,
      error: '',
      subtitle: ''
    };
  },
  mounted() {
    this.fetchData();
    window.addEventListener('resize', this.handleResize);
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize);
    if (this.chart) {
      this.chart.dispose();
    }
  },
  methods: {
    async fetchData() {
      try {
        const response = await fetch(this.endpoint);
        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
        }

        const data = await response.json();
        if (!Array.isArray(data) || data.length === 0) {
          throw new Error('No RRG data available.');
        }

        this.loading = false;
        this.$nextTick(() => {
          this.initChart();
          this.updateChart(data);
        });
      } catch (error) {
        console.error('Error fetching RRG data:', error);
        this.error = 'Unable to load RRG data.';
        this.loading = false;
      }
    },

    initChart() {
      if (!this.chart) {
        this.chart = echarts.init(this.$refs.chartEl);
      }
    },

    updateChart(data) {
      const center = this.center;
      const allPoints = data.flatMap(item => item.tail);
      const latestDates = data
        .map(item => item.latest?.date)
        .filter(Boolean)
        .sort();

      this.subtitle = latestDates.length
        ? `${this.tailDescription} through ${latestDates[latestDates.length - 1]}`
        : '';

      const xValues = allPoints.map(point => point.rs_ratio).concat(center);
      const yValues = allPoints.map(point => point.rs_momentum).concat(center);
      const xExtent = this.getCenteredExtent(xValues);
      const yExtent = this.getCenteredExtent(yValues);

      const backgroundSeries = {
        name: 'quadrants',
        type: 'scatter',
        data: [],
        silent: true,
        markArea: {
          silent: true,
          itemStyle: { opacity: 0.16 },
          data: [
            [
              { name: 'Improving', xAxis: xExtent.min, yAxis: center, itemStyle: { color: '#b1ebff' } },
              { xAxis: center, yAxis: yExtent.max }
            ],
            [
              { name: 'Leading', xAxis: center, yAxis: center, itemStyle: { color: '#bdffc9' } },
              { xAxis: xExtent.max, yAxis: yExtent.max }
            ],
            [
              { name: 'Weakening', xAxis: center, yAxis: yExtent.min, itemStyle: { color: '#fff0a8' } },
              { xAxis: xExtent.max, yAxis: center }
            ],
            [
              { name: 'Lagging', xAxis: xExtent.min, yAxis: yExtent.min, itemStyle: { color: '#ffccd3' } },
              { xAxis: center, yAxis: center }
            ]
          ]
        },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: {
            color: '#444',
            type: 'dashed',
            width: 1
          },
          data: [
            { xAxis: center },
            { yAxis: center }
          ],
          label: { show: false }
        }
      };

      const tailSeries = data.map(item => {
        const color = this.getQuadrantColor(item.latest);
        return {
          name: item.ticker,
          type: 'line',
          data: item.tail.map(point => ({
            value: [point.rs_ratio, point.rs_momentum],
            date: point.date,
            ticker: item.ticker
          })),
          // Straight segments between tail points. A spline through
          // non-monotonic RRG coordinates overshoots and draws loops that are
          // not in the data.
          showSymbol: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            color,
            width: 2,
            opacity: 0.8
          },
          itemStyle: { color },
          emphasis: {
            focus: 'series',
            lineStyle: { width: 4 }
          }
        };
      });

      const latestSeries = {
        name: 'Latest',
        type: 'scatter',
        data: data.map(item => ({
          name: item.ticker,
          value: [item.latest.rs_ratio, item.latest.rs_momentum],
          date: item.latest.date,
          ticker: item.ticker,
          itemStyle: { color: this.getQuadrantColor(item.latest) }
        })),
        symbolSize: 13,
        label: {
          show: true,
          formatter: '{b}',
          position: 'right',
          color: '#222',
          fontSize: 12,
          fontWeight: 600
        },
        labelLayout: {
          hideOverlap: true
        },
        emphasis: {
          scale: 1.4
        }
      };

      this.chart.setOption({
        animation: false,
        grid: {
          left: 78,
          right: 95,
          bottom: 70,
          top: 50,
          containLabel: true
        },
        legend: {
          type: 'scroll',
          top: 5,
          left: 'center',
          itemWidth: 18,
          itemHeight: 8,
          textStyle: { fontSize: 12 },
          data: data.map(item => item.ticker)
        },
        tooltip: {
          trigger: 'item',
          formatter: params => {
            const datum = params.data || {};
            const ticker = datum.ticker || params.seriesName;
            const value = datum.value || [];
            const date = datum.date ? `<br/>Date: ${datum.date}` : '';
            return [
              `<strong>${ticker}</strong>`,
              date,
              `<br/>RS-Ratio: ${this.formatNumber(value[0])}`,
              `<br/>RS-Momentum: ${this.formatNumber(value[1])}`
            ].join('');
          }
        },
        xAxis: {
          name: 'RS-Ratio',
          nameLocation: 'middle',
          nameGap: 38,
          min: xExtent.min,
          max: xExtent.max,
          splitLine: { lineStyle: { color: '#e6e6e6' } },
          axisLabel: { formatter: value => value.toFixed(1) }
        },
        yAxis: {
          name: 'RS-Momentum',
          nameLocation: 'middle',
          nameGap: 52,
          min: yExtent.min,
          max: yExtent.max,
          splitLine: { lineStyle: { color: '#e6e6e6' } },
          axisLabel: { formatter: value => value.toFixed(1) }
        },
        graphic: this.getQuadrantLabels(),
        series: [backgroundSeries, ...tailSeries, latestSeries]
      }, true);
    },

    getCenteredExtent(values) {
      const center = this.center;
      const min = Math.min(...values);
      const max = Math.max(...values);
      // Keep the centre line in the middle of the chart so the quadrants stay
      // equal in size regardless of how far the data has travelled.
      const distance = Math.max(Math.abs(min - center), Math.abs(max - center), this.minimumSpan);
      const padded = distance * 1.18;

      return {
        min: Number((center - padded).toFixed(2)),
        max: Number((center + padded).toFixed(2))
      };
    },

    getQuadrantColor(point) {
      const center = this.center;
      if (point.rs_ratio >= center && point.rs_momentum >= center) return QUADRANT_COLORS.leading;
      if (point.rs_ratio >= center && point.rs_momentum < center) return QUADRANT_COLORS.weakening;
      if (point.rs_ratio < center && point.rs_momentum >= center) return QUADRANT_COLORS.improving;
      return QUADRANT_COLORS.lagging;
    },

    getQuadrantLabels() {
      return [
        this.quadrantLabel('Improving', 0.19, 0.19, QUADRANT_COLORS.improving),
        this.quadrantLabel('Leading', 0.78, 0.19, QUADRANT_COLORS.leading),
        this.quadrantLabel('Lagging', 0.19, 0.82, QUADRANT_COLORS.lagging),
        this.quadrantLabel('Weakening', 0.78, 0.82, QUADRANT_COLORS.weakening)
      ];
    },

    quadrantLabel(text, leftRatio, topRatio, color) {
      return {
        type: 'text',
        left: `${leftRatio * 100}%`,
        top: `${topRatio * 100}%`,
        silent: true,
        style: {
          text,
          fill: color,
          font: '700 14px sans-serif',
          opacity: 0.65
        }
      };
    },

    formatNumber(value) {
      return typeof value === 'number' ? value.toFixed(2) : '-';
    },

    handleResize() {
      if (this.chart) {
        this.chart.resize();
      }
    }
  },
  computed: {
    // Smallest half-width the axes will show, so a quiet week does not get
    // magnified into apparent chaos. The two series live on different scales.
    minimumSpan() {
      return this.center === 0 ? 0.5 : 2;
    }
  }
};
</script>

<style scoped>
.rrg-subtitle {
  color: #666;
  font-size: 14px;
  text-align: center;
  margin-bottom: 16px;
}

.rrg-state {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  color: #666;
  font-size: 18px;
  padding: 50px;
  text-align: center;
}

.rrg-state.error {
  color: #b00020;
}

.rrg-chart {
  width: 100%;
  height: min(74vh, 780px);
  min-height: 560px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
