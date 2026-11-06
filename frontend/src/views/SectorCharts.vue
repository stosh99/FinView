<template>
  <div class="sector-charts">
    <h1>Sector ETF Charts</h1>
    <div v-if="loading" class="loading">Loading chart data...</div>
    <div v-else class="charts-grid">
      <div
        v-for="ticker in tickers"
        :key="ticker"
        class="chart-container"
      >
        <div class="chart-header">
          <h3>{{ ticker }}</h3>
          <p class="etf-name">{{ chartData[ticker]?.name }}</p>
        </div>
        <div :id="`chart-${ticker}`" class="chart"></div>
      </div>
    </div>
  </div>
</template>

<script>
import * as echarts from 'echarts';

export default {
  name: 'SectorCharts',
  data() {
    return {
      loading: true,
      tickers: [],
      charts: {},
      chartData: {}
    };
  },
  mounted() {
    this.fetchData();
  },
  beforeUnmount() {
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
        this.chartData = await response.json();

        // Get tickers in order (SPY first, then others)
        this.tickers = Object.keys(this.chartData);

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

    initCharts() {
      this.tickers.forEach(ticker => {
        const chartDom = document.getElementById(`chart-${ticker}`);
        if (!chartDom) return;

        const chart = echarts.init(chartDom);
        this.charts[ticker] = chart;

        const data = this.chartData[ticker];

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
                formatter: function(value) {
                  // Format date to show MM/DD/YYYY
                  const date = new Date(value);
                  return (date.getMonth() + 1) + '/' + date.getDate() + '/' + date.getFullYear();
                }
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

        chart.setOption(option);
      });

      // Handle window resize
      window.addEventListener('resize', this.handleResize);
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