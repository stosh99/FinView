<template>
  <div class="sector-charts">
    <h1>ETF Charts</h1>
    <div v-if="loading" class="loading">Loading chart data...</div>
    <template v-else>
      <div class="category-filter">
        <button
          class="chip"
          :class="{ active: activeCategories.length === 0 }"
          @click="showAll"
        >
          All
        </button>
        <button
          v-for="group in groups"
          :key="group.category"
          class="chip"
          :class="{ active: activeCategories.includes(group.category) }"
          @click="toggleCategory(group.category)"
        >
          {{ categoryLabel(group.category) }}
        </button>
      </div>

      <section
        v-for="group in groups"
        v-show="isVisible(group.category)"
        :key="group.category"
        class="category-section"
      >
        <h2 class="category-heading">
          {{ categoryLabel(group.category) }}
          <span class="category-count">({{ group.etfs.length }})</span>
          <span v-if="categoryNotes[group.category]" class="category-note">
            {{ categoryNotes[group.category] }}
          </span>
        </h2>
        <div class="charts-grid">
          <div
            v-for="etf in group.etfs"
            :key="etf.ticker"
            class="chart-container"
          >
            <div class="chart-header">
              <h3>{{ etf.ticker }}</h3>
              <p class="etf-name">{{ etf.name }}</p>
              <p v-if="etf.category === 'cash' && etf.rate" class="etf-name">
                Shown as the 3-month T-bill yield (FRED {{ etf.rate.series_id }}), not the fund's price
              </p>
            </div>
            <div :id="`chart-${etf.ticker}`" class="chart"></div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script>
import * as echarts from 'echarts';

// The API sends dates as 'YYYY-MM-DD'; turn that text into M/D/YYYY directly.
// new Date('2026-11-06') is UTC midnight, i.e. the evening before in US time
// zones, so formatting a Date object put every label one day early.
function formatDateLabel(value) {
  const [year, month, day] = value.split('-');
  return `${Number(month)}/${Number(day)}/${year}`;
}

export default {
  name: 'SectorCharts',
  data() {
    return {
      loading: true,
      etfs: [],
      charts: {},
      // Empty means "All". Not persisted; this page has no saved state.
      activeCategories: [],
      categoryLabels: {
        benchmark: 'Benchmark',
        sector: 'US Sectors',
        small_cap: 'Small Cap',
        international: 'International',
        real_asset: 'Real Assets',
        currency: 'Currency',
        cash: 'Cash'
      },
      categoryNotes: {
        benchmark: 'RRG benchmark, not a competitor',
        cash: 'parking slot, not a competitor'
      }
    };
  },
  computed: {
    // The API returns ETFs already in display order, so grouping in order of
    // first appearance keeps categories in that order too.
    groups() {
      const groups = [];
      this.etfs.forEach(etf => {
        let group = groups.find(g => g.category === etf.category);
        if (!group) {
          group = { category: etf.category, etfs: [] };
          groups.push(group);
        }
        group.etfs.push(etf);
      });
      return groups;
    }
  },
  mounted() {
    this.fetchData();
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize);
    // Dispose all charts to prevent memory leaks
    Object.values(this.charts).forEach(chart => {
      if (chart) {
        chart.dispose();
      }
    });
  },
  methods: {
    async fetchData() {
      try {
        const response = await fetch('/api/sector-chart-data');
        this.etfs = await response.json();

        this.loading = false;

        // Wait for DOM update
        this.$nextTick(() => {
          this.initCharts();
        });
      } catch (error) {
        console.error('Error fetching chart data:', error);
        this.loading = false;
      }
    },

    categoryLabel(category) {
      return this.categoryLabels[category] || category;
    },

    isVisible(category) {
      return this.activeCategories.length === 0 || this.activeCategories.includes(category);
    },

    showAll() {
      this.activeCategories = [];
      this.resizeAfterShow();
    },

    toggleCategory(category) {
      const index = this.activeCategories.indexOf(category);
      if (index === -1) {
        this.activeCategories.push(category);
      } else {
        this.activeCategories.splice(index, 1);
      }
      this.resizeAfterShow();
    },

    // Charts drawn while their section was hidden (v-show) have zero size;
    // resize once the section is visible again.
    resizeAfterShow() {
      this.$nextTick(() => this.handleResize());
    },

    initCharts() {
      this.etfs.forEach(data => {
        const ticker = data.ticker;
        const chartDom = document.getElementById(`chart-${ticker}`);
        if (!chartDom) return;

        const chart = echarts.init(chartDom);
        this.charts[ticker] = chart;

        // A T-bill fund's price just creeps up, so candles and trend
        // indicators are noise. Cash is shown as the T-bill yield instead.
        // That is the market rate, not BIL's own yield (see the card subtitle).
        const option = data.category === 'cash' && data.rate
          ? this.yieldOption(data)
          : this.candlestickOption(data);
        chart.setOption(option);
      });

      // Handle window resize
      window.addEventListener('resize', this.handleResize);
    },

    candlestickOption(data) {
      const ticker = data.ticker;

      // Prepare data for ECharts
      const dates = data.dates;
      // The API sends [open, high, low, close]; ECharts candlesticks expect
      // [open, close, low, high]. Without this reorder ECharts reads the high
      // as the close, so every candle looks like an up day.
      const ohlc = data.ohlc.map(([open, high, low, close]) => [open, close, low, high]);

      // One colour per indicator, applied to both lineStyle (the drawn line)
      // and itemStyle (what the legend swatch is filled from) so the two
      // cannot drift apart. Same pattern as RRG.vue.
      const indicatorColors = {
        sma50: '#2196F3',
        sma200: '#FF9800',
        ema21: '#9C27B0'
      };

      const option = {
        animation: false,
        legend: {
          data: ['SMA50', 'SMA200', 'EMA21'],
          top: 0,
          left: 'center',
          textStyle: {
            fontSize: 12
          },
          icon: 'rect',
          itemWidth: 25,
          itemHeight: 2
        },
        grid: [
          {
            left: '10%',
            right: '8%',
            top: '12%',
            height: '63%'
          },
          {
            left: '10%',
            right: '8%',
            top: '80%',
            height: '10%'
          }
        ],
        xAxis: [
          {
            type: 'category',
            data: dates,
            scale: true,
            boundaryGap: false,
            axisLine: { onZero: false },
            splitLine: { show: false },
            min: 'dataMin',
            max: 'dataMax',
            axisLabel: {
              show: true,
              rotate: 45,
              fontSize: 10,
              // Always label the newest candle; ECharts hides the neighbouring
              // label instead if the two would overlap.
              showMaxLabel: true,
              formatter: formatDateLabel
            }
          },
          {
            type: 'category',
            gridIndex: 1,
            data: dates,
            scale: true,
            boundaryGap: false,
            axisLine: { onZero: false },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: { show: false },
            min: 'dataMin',
            max: 'dataMax'
          }
        ],
        yAxis: [
          {
            scale: true,
            splitArea: {
              show: true
            }
          },
          {
            scale: true,
            gridIndex: 1,
            splitNumber: 2,
            position: 'right',
            axisLabel: {
              show: true,
              fontSize: 10
            },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { show: false }
          }
        ],
        dataZoom: [
          {
            type: 'inside',
            xAxisIndex: [0, 1],
            start: 0,
            end: 100
          },
          {
            show: true,
            xAxisIndex: [0, 1],
            type: 'slider',
            bottom: '5%',
            start: 0,
            end: 100
          }
        ],
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          borderWidth: 1,
          borderColor: '#ccc',
          padding: 10,
          textStyle: {
            color: '#000'
          },
          valueFormatter: (value) => {
            if (value === null || value === undefined) return '-';
            return typeof value === 'number' ? value.toFixed(2) : value;
          }
        },
        series: [
          {
            name: ticker,
            type: 'candlestick',
            data: ohlc,
            itemStyle: {
              color: '#26a69a',
              color0: '#ef5350',
              borderColor: '#26a69a',
              borderColor0: '#ef5350'
            }
          },
          {
            name: 'SMA50',
            type: 'line',
            data: data.sma50,
            smooth: true,
            lineStyle: {
              opacity: 0.8,
              width: 1.5,
              color: indicatorColors.sma50
            },
            itemStyle: { color: indicatorColors.sma50 },
            showSymbol: false
          },
          {
            name: 'SMA200',
            type: 'line',
            data: data.sma200,
            smooth: true,
            lineStyle: {
              opacity: 0.8,
              width: 1.5,
              color: indicatorColors.sma200
            },
            itemStyle: { color: indicatorColors.sma200 },
            showSymbol: false
          },
          {
            name: 'EMA21',
            type: 'line',
            data: data.ema21,
            smooth: true,
            lineStyle: {
              opacity: 0.8,
              width: 1.5,
              color: indicatorColors.ema21
            },
            itemStyle: { color: indicatorColors.ema21 },
            showSymbol: false
          },
          {
            name: 'Bollinger Upper',
            type: 'line',
            data: data.boll_up,
            smooth: true,
            lineStyle: {
              opacity: 0.5,
              width: 1,
              color: '#607D8B'
            },
            showSymbol: false
          },
          {
            name: 'Bollinger Lower',
            type: 'line',
            data: data.boll_dn,
            smooth: true,
            lineStyle: {
              opacity: 0.5,
              width: 1,
              color: '#607D8B'
            },
            showSymbol: false
          },
          {
            name: 'Volume',
            type: 'bar',
            xAxisIndex: 1,
            yAxisIndex: 1,
            data: data.volume,
            itemStyle: {
              color: '#7fbe9e'
            }
          }
        ]
      };

      return option;
    },

    yieldOption(data) {
      const rate = data.rate;
      return {
        animation: false,
        grid: { left: '10%', right: '8%', top: '8%', height: '67%' },
        xAxis: {
          type: 'category',
          data: rate.dates,
          boundaryGap: false,
          axisLabel: {
            rotate: 45,
            fontSize: 10,
            showMaxLabel: true,
            formatter: formatDateLabel
          }
        },
        yAxis: {
          scale: true,
          splitArea: { show: true },
          axisLabel: { formatter: value => value.toFixed(2) + '%' }
        },
        dataZoom: [
          { type: 'inside', start: 0, end: 100 },
          { show: true, type: 'slider', bottom: '5%', start: 0, end: 100 }
        ],
        tooltip: {
          trigger: 'axis',
          borderWidth: 1,
          borderColor: '#ccc',
          padding: 10,
          textStyle: { color: '#000' },
          valueFormatter: (value) => {
            if (value === null || value === undefined) return '-';
            return value.toFixed(2) + '%';
          }
        },
        series: [
          {
            name: `3-mo T-bill yield (FRED ${rate.series_id})`,
            type: 'line',
            data: rate.values,
            showSymbol: false,
            lineStyle: { width: 1.5, color: '#1976D2' },
            itemStyle: { color: '#1976D2' }
          }
        ]
      };
    },

    handleResize() {
      Object.values(this.charts).forEach(chart => {
        if (chart) {
          chart.resize();
        }
      });
    }
  }
};
</script>

<style scoped>
.sector-charts {
  padding: 20px;
  max-width: 1800px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

.category-filter {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  margin-bottom: 20px;
}

.chip {
  border: 1px solid #1976D2;
  background: white;
  color: #1976D2;
  border-radius: 16px;
  padding: 6px 14px;
  font-size: 14px;
  cursor: pointer;
}

.chip.active {
  background: #1976D2;
  color: white;
}

.category-section {
  margin-bottom: 20px;
}

.category-heading {
  font-size: 20px;
  color: #333;
  border-bottom: 2px solid #1976D2;
  padding-bottom: 6px;
}

.category-count {
  color: #666;
  font-weight: normal;
  font-size: 16px;
}

.category-note {
  color: #888;
  font-weight: normal;
  font-size: 13px;
  font-style: italic;
  margin-left: 8px;
}

.loading {
  text-align: center;
  padding: 50px;
  font-size: 18px;
  color: #666;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 30px;
  padding: 20px 0;
}

.chart-container {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.chart-header {
  text-align: center;
  margin-bottom: 10px;
}

.chart-container h3 {
  margin: 0;
  color: #1976D2;
  font-size: 18px;
}

.etf-name {
  margin: 4px 0 0 0;
  color: #666;
  font-size: 13px;
  font-weight: normal;
}

.chart {
  width: 100%;
  height: 400px;
}

@media (max-width: 1400px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>