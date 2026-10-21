<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { createChart, CandlestickSeries, LineSeries, HistogramSeries, ColorType, type IChartApi, type Time } from 'lightweight-charts';
import { useSettings } from '../stores/settings';
const props = defineProps<{bars?:Record<string,any>[]; equity?:Record<string,any>[]; adjusted?:boolean; drawdown?:boolean; sourceLabel?:string; recentBars?:number; levels?:{price:number;title:string;color:string}[]}>();
const host = ref<HTMLElement>();
const settings = useSettings();
let chart:IChartApi|undefined;
function render() {
  chart?.remove();
  if (!host.value) return;
  chart = createChart(host.value,{autoSize:true,height:380,layout:{background:{type:ColorType.Solid,color:settings.dark?'#111b2b':'#ffffff'},textColor:settings.dark?'#b2bfd1':'#35465e',attributionLogo:true},grid:{vertLines:{color:settings.dark?'#243247':'#eef1f5'},horzLines:{color:settings.dark?'#243247':'#eef1f5'}}});
  if (props.bars?.length) {
    const candles = chart.addSeries(CandlestickSeries,{upColor:'#14b8a6',downColor:'#ef4444',wickUpColor:'#14b8a6',wickDownColor:'#ef4444',borderVisible:false});
    for(const line of props.levels??[])candles.createPriceLine({...line,lineWidth:1,axisLabelVisible:true});
    candles.setData(props.bars.map(b=>{const f=props.adjusted?Number(b.factor):1;return {time:b.session_date as Time,open:Number(b.open)*f,high:Number(b.high)*f,low:Number(b.low)*f,close:Number(b.close)*f};}));
    const volumes=chart.addSeries(HistogramSeries,{priceFormat:{type:'volume'},priceScaleId:'volume'});
    volumes.priceScale().applyOptions({scaleMargins:{top:.82,bottom:0}});
    volumes.setData(props.bars.map(b=>({time:b.session_date as Time,value:b.volume,color:Number(b.close)>=Number(b.open)?'#14b8a650':'#ef444450'})));
    for(const [period,color] of [[20,'#38bdf8'],[50,'#fbbf24'],[200,'#a78bfa']] as const) {
      const values=props.bars.map(b=>Number(b.close)*(props.adjusted?Number(b.factor):1));
      const data:{time:Time;value:number}[]=[];let value=0;
      for(let i=0;i<values.length;i++){if(i<period)value+=values[i]/period;if(i>=period)value+=(2/(period+1))*(values[i]-value);if(i>=period-1)data.push({time:props.bars[i].session_date as Time,value});}
      chart.addSeries(LineSeries,{color,lineWidth:1,title:`EMA${period}`}).setData(data);
    }
  }
  if(props.equity?.length && props.drawdown){
    chart.addSeries(LineSeries,{color:'#ef4444',lineWidth:2,title:'Drawdown %'}).setData(props.equity.map(p=>({time:p.session_date as Time,value:Number(p.drawdown)*100})));
  } else if(props.equity?.length) {
    chart.addSeries(LineSeries,{color:'#14b8a6',lineWidth:2,title:'NAV'}).setData(props.equity.map(p=>({time:p.session_date as Time,value:Number(p.nav)})));
    chart.addSeries(LineSeries,{color:'#fbbf24',lineWidth:1,title:'VNINDEX price benchmark'}).setData(props.equity.map(p=>({time:p.session_date as Time,value:Number(p.benchmark)})));
  }
  chart.timeScale().fitContent();
  if(props.recentBars&&props.bars?.length)chart.timeScale().setVisibleLogicalRange({from:Math.max(0,props.bars.length-props.recentBars),to:props.bars.length});
}
onMounted(render);watch(()=>[props.bars,props.equity,props.adjusted,props.levels,settings.dark],render);
onUnmounted(()=>chart?.remove());
</script>
<template><div ref="host" style="height:380px;width:100%" role="img" aria-label="Biểu đồ dữ liệu nghiên cứu" /><small class="muted">Charts by <a href="https://www.tradingview.com/" target="_blank" rel="noopener">TradingView Lightweight Charts</a> · {{props.sourceLabel??'Dữ liệu DEMO khi có nhãn DEMO.'}}</small></template>
