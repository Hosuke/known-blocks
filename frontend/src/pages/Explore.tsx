import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import * as d3 from 'd3';
import { Icon } from '../components/Icon';
import { Shimmer } from '../components/Loading';
import { useLang } from '../lib/lang';
import { api } from '../lib/api';

type Tab = 'timeline' | 'people' | 'map';

interface Person { name: string; name_local?: string; dates?: string; role?: string; articles: string[] }
interface Event { name: string; name_local?: string; date?: string; description?: string; articles: string[] }
interface Place { name: string; name_local?: string; coords?: [number, number] | null; articles: string[] }

/** Parse date strings like "c.372-289 BCE", "1190 CE", "384-414" into a numeric year. */
function parseYear(dateStr?: string): number | null {
  if (!dateStr) return null;
  const s = dateStr.replace(/c\.\s*/i, '').replace(/\s+/g, '');
  // "372-289 BCE" → take first number, negate for BCE
  const bce = /bce|bc/i.test(s);
  const match = s.match(/(\d+)/);
  if (!match) return null;
  const year = parseInt(match[1]);
  return bce ? -year : year;
}

export function Explore() {
  const navigate = useNavigate();
  const { lang } = useLang();
  const zh = lang === 'zh' || lang === 'zh-en';
  const [tab, setTab] = useState<Tab>('timeline');
  const [people, setPeople] = useState<Person[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [places, setPlaces] = useState<Place[]>([]);
  const [loading, setLoading] = useState(true);
  const [articleCount, setArticleCount] = useState(0);
  const [filter, setFilter] = useState<'all' | 'people' | 'events'>('all');
  const [hovered, setHovered] = useState<{ name: string; dates: string; role?: string; x: number; y: number } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    api.getEntities().then(data => {
      setPeople(data.people || []);
      setEvents(data.events || []);
      setPlaces(data.places || []);
      setArticleCount(data.article_count || 0);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const displayName = (entity: { name: string; name_local?: string }) =>
    (zh && entity.name_local) ? entity.name_local : entity.name;

  // Build timeline items with parsed years
  const timelineItems = useMemo(() => {
    const items: { name: string; localName: string; year: number; type: 'person' | 'event'; dates: string; role?: string; description?: string; slug?: string }[] = [];

    if (filter === 'all' || filter === 'people') {
      for (const p of people) {
        const year = parseYear(p.dates);
        if (year !== null) {
          items.push({
            name: p.name, localName: p.name_local || p.name,
            year, type: 'person', dates: p.dates || '',
            role: p.role, slug: p.articles[0],
          });
        }
      }
    }
    if (filter === 'all' || filter === 'events') {
      for (const e of events) {
        const year = parseYear(e.date);
        if (year !== null) {
          items.push({
            name: e.name, localName: e.name_local || e.name,
            year, type: 'event', dates: e.date || '',
            description: e.description, slug: e.articles[0],
          });
        }
      }
    }

    return items.sort((a, b) => a.year - b.year);
  }, [people, events, filter]);

  // D3 horizontal timeline
  useEffect(() => {
    if (tab !== 'timeline' || !svgRef.current || timelineItems.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = 280;
    const margin = { top: 40, right: 40, bottom: 50, left: 40 };

    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const minYear = d3.min(timelineItems, d => d.year) ?? -500;
    const maxYear = d3.max(timelineItems, d => d.year) ?? 2000;
    const padding = Math.max(50, (maxYear - minYear) * 0.05);

    const x = d3.scaleLinear()
      .domain([minYear - padding, maxYear + padding])
      .range([margin.left, width - margin.right]);

    // Axis
    const axisG = svg.append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`);

    axisG.call(
      d3.axisBottom(x)
        .tickFormat(d => {
          const v = d as number;
          return v < 0 ? `${Math.abs(v)} BCE` : `${v}`;
        })
    );
    axisG.selectAll('text').attr('fill', '#9ca3af').style('font-size', '10px');
    axisG.selectAll('line').attr('stroke', '#374151');
    axisG.select('.domain').attr('stroke', '#374151');

    // Timeline line
    svg.append('line')
      .attr('x1', margin.left).attr('x2', width - margin.right)
      .attr('y1', height / 2).attr('y2', height / 2)
      .attr('stroke', '#374151').attr('stroke-width', 1);

    // Stagger items vertically to avoid overlap
    const used: number[] = [];
    function getRow(xPos: number): number {
      for (let row = 0; row < 4; row++) {
        const key = Math.round(xPos / 60) * 100 + row;
        if (!used.includes(key)) {
          used.push(key);
          return row;
        }
      }
      return Math.floor(Math.random() * 4);
    }

    // Draw items
    const items = svg.selectAll('.timeline-item')
      .data(timelineItems)
      .enter()
      .append('g')
      .attr('class', 'timeline-item')
      .attr('cursor', 'pointer')
      .on('click', (_, d) => { if (d.slug) navigate(`/wiki/${d.slug}`); });

    items.each(function (d) {
      const g = d3.select(this);
      const cx = x(d.year);
      const row = getRow(cx);
      const above = row % 2 === 0;
      const offset = (Math.floor(row / 2) + 1) * 36;
      const cy = height / 2 + (above ? -offset : offset);

      // Stem line
      g.append('line')
        .attr('x1', cx).attr('x2', cx)
        .attr('y1', height / 2).attr('y2', cy)
        .attr('stroke', d.type === 'person' ? '#60a5fa' : '#fbbf24')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '2,2');

      // Dot
      g.append('circle')
        .attr('cx', cx).attr('cy', cy).attr('r', 5)
        .attr('fill', d.type === 'person' ? '#60a5fa' : '#fbbf24')
        .attr('stroke', '#1f2937').attr('stroke-width', 1.5);

      // Label
      g.append('text')
        .attr('x', cx).attr('y', cy + (above ? -12 : 16))
        .attr('text-anchor', 'middle')
        .attr('fill', '#d1d5db')
        .style('font-size', '11px')
        .text(zh ? (d.localName.length > 6 ? d.localName.slice(0, 6) + '…' : d.localName) : (d.name.length > 12 ? d.name.slice(0, 12) + '…' : d.name));
    });

    // Hover interaction
    items.on('mouseenter', function (event, d) {
      const cx = x(d.year);
      setHovered({ name: zh ? d.localName : d.name, dates: d.dates, role: d.role || d.description, x: cx, y: 20 });
      d3.select(this).select('circle').transition().duration(150).attr('r', 8);
    }).on('mouseleave', function () {
      setHovered(null);
      d3.select(this).select('circle').transition().duration(150).attr('r', 5);
    });

    // Zoom + pan
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.5, 10])
      .on('zoom', (event) => {
        const newX = event.transform.rescaleX(x);
        axisG.call(d3.axisBottom(newX).tickFormat(d => {
          const v = d as number;
          return v < 0 ? `${Math.abs(v)} BCE` : `${v}`;
        }));
        axisG.selectAll('text').attr('fill', '#9ca3af').style('font-size', '10px');
        axisG.selectAll('line').attr('stroke', '#374151');
        axisG.select('.domain').attr('stroke', '#374151');

        items.each(function (d) {
          const g = d3.select(this);
          const cx = newX(d.year);
          g.select('line').attr('x1', cx).attr('x2', cx);
          g.select('circle').attr('cx', cx);
          g.select('text').attr('x', cx);
        });

        svg.select('line:not(.timeline-item line)')
          .attr('x1', newX(minYear - padding))
          .attr('x2', newX(maxYear + padding));
      });

    svg.call(zoom);

  }, [tab, timelineItems, zh, navigate]);

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'timeline', label: zh ? '时间线' : 'Timeline', icon: 'timeline' },
    { id: 'people', label: zh ? '人物' : 'People', icon: 'groups' },
    { id: 'map', label: zh ? '地图' : 'Map', icon: 'map' },
  ];

  const isEmpty = people.length === 0 && events.length === 0 && places.length === 0;

  return (
    <div className="p-8 max-w-[1100px] mx-auto">
      <h1 className="font-headline text-3xl font-bold mb-6">{zh ? '探索' : 'Explore'}</h1>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-outline-variant/30">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm transition-colors border-b-2 ${
              tab === t.id
                ? 'border-primary text-primary font-medium'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            }`}>
            <Icon name={t.icon} className="text-[16px]" />
            {t.label}
          </button>
        ))}
      </div>

      {loading && <Shimmer lines={8} />}

      {!loading && isEmpty && (
        <div className="text-center py-16 text-on-surface-variant">
          <Icon name="explore" className="text-5xl mb-3 block" />
          <p className="mb-4">{zh ? '尚未提取实体。请在设置中启用 entities 功能。' : 'No entities extracted yet. Enable entities in config.'}</p>
          <code className="text-xs bg-surface-container px-3 py-1.5 rounded-lg">entities: {'{'} enabled: true {'}'}</code>
        </div>
      )}

      {/* Timeline Tab — D3 horizontal axis */}
      {!loading && tab === 'timeline' && !isEmpty && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex gap-2">
              {(['all', 'people', 'events'] as const).map(f => (
                <button key={f} onClick={() => setFilter(f)}
                  className={`px-3 py-1 text-xs rounded-full transition-colors ${
                    filter === f ? 'bg-primary/15 text-primary' : 'bg-surface-container text-on-surface-variant'
                  }`}>
                  {f === 'all' ? (zh ? '全部' : 'All') :
                   f === 'people' ? (zh ? '人物' : 'People') : (zh ? '事件' : 'Events')}
                </button>
              ))}
            </div>
            <span className="text-[10px] text-outline">{zh ? '滚轮缩放，拖拽平移' : 'Scroll to zoom, drag to pan'}</span>
          </div>

          <div className="relative bg-surface-container rounded-xl border border-outline-variant/20 overflow-hidden">
            <svg ref={svgRef} className="w-full" style={{ height: 280 }} />
            {hovered && (
              <div className="absolute bg-surface-container-highest border border-outline-variant/30 rounded-lg px-3 py-2 shadow-lg pointer-events-none text-sm"
                style={{ left: Math.min(hovered.x, 800), top: hovered.y }}>
                <div className="font-medium">{hovered.name}</div>
                <div className="text-xs text-outline">{hovered.dates}</div>
                {hovered.role && <div className="text-xs text-on-surface-variant">{hovered.role}</div>}
              </div>
            )}
          </div>

          {timelineItems.length === 0 && (
            <div className="text-center py-8 text-on-surface-variant text-sm">
              {zh ? '没有可用日期的实体。实体需要包含日期信息才能显示在时间线上。' : 'No entities with parseable dates.'}
            </div>
          )}
        </div>
      )}

      {/* People Tab */}
      {!loading && tab === 'people' && !isEmpty && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {people.map((p, i) => (
            <div key={i} className="bg-surface-container rounded-xl p-5 border border-outline-variant/20 hover:border-primary/30 transition-colors cursor-pointer"
              onClick={() => p.articles[0] && navigate(`/wiki/${p.articles[0]}`)}>
              <div className="font-medium mb-1">{displayName(p)}</div>
              {p.name_local && p.name !== p.name_local && (
                <div className="text-xs text-on-surface-variant mb-2">{zh ? p.name : p.name_local}</div>
              )}
              <div className="flex items-center justify-between text-xs text-outline">
                <span>{p.dates || '—'}</span>
                <span>{p.role}</span>
              </div>
              <div className="mt-2 text-[10px] text-outline">{p.articles.length} {zh ? '篇相关文章' : 'related articles'}</div>
            </div>
          ))}
        </div>
      )}

      {/* Map Tab */}
      {!loading && tab === 'map' && (
        <div className="bg-surface-container rounded-xl p-8 border border-outline-variant/20 text-center">
          <Icon name="map" className="text-5xl text-on-surface-variant mb-3 block" />
          <p className="text-on-surface-variant mb-2">{zh ? '地图视图' : 'Map View'}</p>
          <p className="text-xs text-outline">
            {places.length > 0
              ? `${places.length} ${zh ? '个地点已提取' : 'places extracted'}`
              : (zh ? '需要在实体数据中包含坐标信息' : 'Requires coordinates in entity data')}
          </p>
          {places.length > 0 && (
            <div className="mt-4 space-y-2 max-w-md mx-auto text-left">
              {places.map((p, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <Icon name="place" className="text-error text-[16px]" />
                  <span>{displayName(p)}</span>
                  <span className="text-[10px] text-outline ml-auto">
                    {p.coords ? `${p.coords[0].toFixed(1)}, ${p.coords[1].toFixed(1)}` : '—'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Stats banner */}
      {!isEmpty && (
        <div className="mt-8 text-center text-xs text-outline">
          {zh ? '实体提取' : 'Entity extraction'}: {people.length} {zh ? '人物' : 'people'}, {events.length} {zh ? '事件' : 'events'}, {places.length} {zh ? '地点' : 'places'} — {zh ? '来自' : 'from'} {articleCount} {zh ? '篇文章' : 'articles'}
        </div>
      )}
    </div>
  );
}
