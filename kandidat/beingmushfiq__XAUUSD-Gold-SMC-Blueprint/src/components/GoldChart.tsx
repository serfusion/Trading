import React, { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi, SeriesMarker, Time, ColorType, CandlestickSeries } from 'lightweight-charts';
import { useStore } from '../store/useStore';
import { SignalType } from '../types/trading';

export const GoldChart: React.FC = () => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [chartApi, setChartApi] = useState<IChartApi | null>(null);
  const [seriesApi, setSeriesApi] = useState<ISeriesApi<"Candlestick"> | null>(null);
  const priceLineRefs = useRef<any[]>([]);
  const initialDataLoaded = useRef(false);

  const tickData = useStore(state => state.tickData);
  const markings = useStore(state => state.smcMarkings);
  const activeSetup = useStore(state => state.activeSetup);
  const currentPrice = useStore(state => state.currentPrice);

  // Initialize TV lightweight-charts
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#080809' },
        textColor: 'rgba(255, 255, 255, 0.5)',
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
      },
      crosshair: {
        mode: 0, // Normal crosshair
        vertLine: { width: 1, color: 'rgba(255, 255, 255, 0.1)', style: 1 },
        horzLine: { width: 1, color: 'rgba(255, 255, 255, 0.1)', style: 1 },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.1)',
      },
      autoSize: true,
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    setChartApi(chart);
    setSeriesApi(series);

    return () => {
      chart.remove();
    };
  }, []);

  // Sync Live Data
  useEffect(() => {
    if (!seriesApi || tickData.length === 0) return;

    // Convert JS Date to strict Unix timestamp expected by Lightweight Charts
    const formattedData = tickData.map(d => ({
      time: (Math.floor(d.time.getTime() / 1000)) as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    // Ensure strictly chronological data
    formattedData.sort((a, b) => (a.time as number) - (b.time as number));
    
    // Ensure unique times
    const uniqueData = formattedData.filter((v, i, a) => a.findIndex(t => (t.time === v.time)) === i);

    if (!initialDataLoaded.current && uniqueData.length > 5) {
      // Heavy bulk initialization from REST API bootstrap
      seriesApi.setData(uniqueData);
      
      if (chartApi) {
         chartApi.timeScale().fitContent();
      }
      initialDataLoaded.current = true;
    } else if (initialDataLoaded.current && uniqueData.length > 0) {
      // Light real-time update over WebSocket
      seriesApi.update(uniqueData[uniqueData.length - 1]);
    }
  }, [tickData, seriesApi, chartApi]);

  // Sync SMC Markings to Price Lines
  useEffect(() => {
    if (!seriesApi) return;

    // Cleanup old lines securely
    priceLineRefs.current.forEach(line => {
      try { seriesApi.removePriceLine(line); } catch (e) {}
    });
    priceLineRefs.current = [];

    // Redraw current market structure
    markings.forEach(m => {
      if (m.type === SignalType.BOS || m.type === SignalType.CHOCH) {
        const isBull = m.label.includes('▲') || m.label.includes('BULL');
        const color = isBull ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)';
        
        const line = seriesApi.createPriceLine({
          price: m.price,
          color: color,
          lineWidth: 2,
          lineStyle: 2, // Dashed
          axisLabelVisible: true,
          title: m.label,
        });
        priceLineRefs.current.push(line);
      } 
      else if (m.type === SignalType.FVG) {
        // Since we can't draw shaded rectangles natively, we use dotted bounds
        const lineTop = seriesApi.createPriceLine({
          price: Math.max(m.price, m.priceEnd ?? m.price),
          color: 'rgba(251, 191, 36, 0.4)',
          lineWidth: 1,
          lineStyle: 3, // Dotted
          title: 'FVG High',
        });
        const lineBot = seriesApi.createPriceLine({
          price: Math.min(m.price, m.priceEnd ?? m.price),
          color: 'rgba(251, 191, 36, 0.4)',
          lineWidth: 1,
          lineStyle: 3,
        });
        priceLineRefs.current.push(lineTop, lineBot);
      } 
      else if (m.type === SignalType.OB) {
        const lineTop = seriesApi.createPriceLine({
          price: Math.max(m.price, m.priceEnd ?? m.price),
          color: 'rgba(168, 85, 247, 0.5)',
          lineWidth: 1,
          lineStyle: 1, // Solid
          title: m.label,
        });
        const lineBot = seriesApi.createPriceLine({
          price: Math.min(m.price, m.priceEnd ?? m.price),
          color: 'rgba(168, 85, 247, 0.5)',
          lineWidth: 1,
          lineStyle: 1,
        });
        priceLineRefs.current.push(lineTop, lineBot);
      }
    });

  }, [markings, seriesApi]);

  // Sync Hardware Buy/Sell Signals
  useEffect(() => {
    if (!seriesApi || tickData.length === 0) return;

    let markers: SeriesMarker<Time>[] = [];

    if (activeSetup && activeSetup.status === 'PENDING') {
      const match = tickData.find(d => Math.abs(d.time.getTime() - activeSetup.timestamp.getTime()) < 60000);
      const signalTime = match 
        ? (Math.floor(match.time.getTime() / 1000) as Time) 
        : (Math.floor(tickData[tickData.length - 1].time.getTime() / 1000) as Time);

      const isBuy = activeSetup.type === 'BUY';

      markers.push({
        time: signalTime,
        position: isBuy ? 'belowBar' : 'aboveBar',
        color: isBuy ? '#10b981' : '#ef4444',
        shape: isBuy ? 'arrowUp' : 'arrowDown',
        text: `⚡ ${activeSetup.type} SIGNAL\n(${activeSetup.lotSize} Lots)`,
        size: 2,
      });
    }

    try {
      seriesApi.setMarkers(markers);
    } catch (e) {
      console.warn("Failed to set markers", e);
    }
  }, [activeSetup, tickData, seriesApi]);

  return (
    <div className="relative w-full h-[480px]">
      <div 
        ref={chartContainerRef}
        className="w-full h-full bg-[#080809] border border-white/[0.06] rounded-2xl overflow-hidden" 
        style={{ boxShadow: '0 4px 40px rgba(0,0,0,0.5)' }}
      />
    </div>
  );
};
