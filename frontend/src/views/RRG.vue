<template>
  <div>
    <h1>Relative Rotation Graph</h1>
    <div id="chart" style="width: 800px; height: 600px;"></div>
  </div>
</template>

<script>
import * as echarts from 'echarts';

export default {
  name: 'RRG',
  data() {
    return {
      chart: null,
    };
  },
  mounted() {
    this.initChart();
    this.fetchData();
  },
  methods: {
    initChart() {
      this.chart = echarts.init(document.getElementById('chart'));
      this.chart.setOption({
        grid: {
          left: '10%',
          right: '10%',
          bottom: '10%',
          top: '10%',
          containLabel: true
        },
        xAxis: {
          name: 'RS-Ratio',
          nameLocation: 'middle',
          nameGap: 30,
          splitLine: { show: false },
          axisLine: {
            onZero: true
          },
          axisTick: {
            alignWithLabel: true
          }
        },
        yAxis: {
          name: 'RS-Momentum',
          nameLocation: 'middle',
          nameGap: 50,
          splitLine: { show: false },
          axisLine: {
            onZero: true
          }
        },
        series: [
          {
            type: 'scatter',
            data: [],
          },
        ],
      });
    },
    async fetchData() {
      try {
        const response = await fetch('/api/rrg-data');
        const data = await response.json();
        this.updateChart(data);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    },
    updateChart(data) {
      const chartData = data.map(item => ({
        name: item.ticker,
        value: [item.rs_ratio, item.rs_momentum],
      }));
      this.chart.setOption({
        series: [
          {
            data: chartData,
          },
        ],
      });
    },
  },
};
</script>