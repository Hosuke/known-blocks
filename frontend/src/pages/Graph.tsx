import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import * as d3 from 'd3';
import { Icon } from '../components/Icon';
import { Loading } from '../components/Loading';
import { useLang, localizeTitle } from '../lib/lang';
import { api, type Article } from '../lib/api';

interface Node extends d3.SimulationNodeDatum {
  id: string; title: string; localTitle: string;
  tags: string[]; size: number; summary: string;
  linkCount: number;
}
interface Link extends d3.SimulationLinkDatum<Node> { source: string | Node; target: string | Node; }

const PALETTE = ['#bdc2ff', '#5de6ff', '#45dfa4', '#ffb4ab', '#cccfff', '#00cbe6', '#f0abfc', '#fbbf24'];

export function Graph() {
  const navigate = useNavigate();
  const { lang } = useLang();
  const svgRef = useRef<SVGSVGElement>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [hovered, setHovered] = useState<Node | null>(null);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);

  useEffect(() => {
    api.getArticles().then(a => { setArticles(a); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  // All unique tags
  const allTags = [...new Set(articles.flatMap(a => a.tags || []))].sort();
  const tagColors: Record<string, string> = {};
  allTags.forEach((t, i) => { tagColors[t] = PALETTE[i % PALETTE.length]; });

  useEffect(() => {
    if (!svgRef.current || articles.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth;
    const height = svgRef.current.clientHeight;

    // Filter by tag
    const filtered = selectedTag
      ? articles.filter(a => a.tags?.includes(selectedTag))
      : articles;

    // Build links from shared tags
    const links: Link[] = [];
    for (let i = 0; i < filtered.length; i++) {
      for (let j = i + 1; j < filtered.length; j++) {
        const shared = filtered[i].tags?.filter(t => filtered[j].tags?.includes(t)) || [];
        if (shared.length > 0) {
          links.push({ source: filtered[i].slug, target: filtered[j].slug });
        }
      }
    }

    // Count links per node
    const linkCounts: Record<string, number> = {};
    links.forEach(l => {
      const s = typeof l.source === 'string' ? l.source : l.source.id;
      const t = typeof l.target === 'string' ? l.target : l.target.id;
      linkCounts[s] = (linkCounts[s] || 0) + 1;
      linkCounts[t] = (linkCounts[t] || 0) + 1;
    });

    const nodes: Node[] = filtered.map(a => ({
      id: a.slug,
      title: a.title,
      localTitle: localizeTitle(a.title, lang),
      tags: a.tags || [],
      summary: a.summary || '',
      size: 6 + Math.min((linkCounts[a.slug] || 0) * 3, 20),
      linkCount: linkCounts[a.slug] || 0,
    }));

    const g = svg.append('g');

    // Zoom
    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.2, 5])
        .on('zoom', (e) => g.attr('transform', e.transform))
    );

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink<Node, Link>(links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-250))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => (d as Node).size + 15));

    // Link lines
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', 'var(--c-outline-variant)')
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.4);

    // Node circles with glow
    const node = g.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', d => d.size)
      .attr('fill', d => tagColors[d.tags[0]] || '#8f909e')
      .attr('fill-opacity', 0.85)
      .attr('stroke', d => tagColors[d.tags[0]] || '#8f909e')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.3)
      .style('cursor', 'pointer')
      .on('click', (_, d) => navigate(`/wiki/${d.id}`))
      .on('mouseenter', (_, d) => setHovered(d))
      .on('mouseleave', () => setHovered(null))
      .call(d3.drag<SVGCircleElement, Node>()
        .on('start', (e, d) => { if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on('end', (e, d) => { if (!e.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; })
      );

    // Labels
    const label = g.append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .text(d => d.localTitle)
      .attr('font-size', 11)
      .attr('font-family', lang === 'en' ? 'Inter' : 'Noto Serif SC, serif')
      .attr('fill', 'var(--c-on-surface-variant)')
      .attr('text-anchor', 'middle')
      .attr('dy', d => d.size + 14)
      .style('pointer-events', 'none')
      .style('display', showLabels ? 'block' : 'none');

    // Hover highlight
    node.on('mouseenter', function(_, d) {
      setHovered(d);
      const connected = new Set<string>([d.id]);
      links.forEach(l => {
        const s = typeof l.source === 'string' ? l.source : l.source.id;
        const t = typeof l.target === 'string' ? l.target : l.target.id;
        if (s === d.id) connected.add(t);
        if (t === d.id) connected.add(s);
      });
      node.attr('fill-opacity', n => connected.has(n.id) ? 1 : 0.1);
      node.attr('stroke-opacity', n => connected.has(n.id) ? 0.6 : 0.05);
      link.attr('stroke-opacity', l => {
        const s = typeof l.source === 'string' ? l.source : (l.source as Node).id;
        const t = typeof l.target === 'string' ? l.target : (l.target as Node).id;
        return s === d.id || t === d.id ? 0.8 : 0.03;
      });
      link.attr('stroke-width', l => {
        const s = typeof l.source === 'string' ? l.source : (l.source as Node).id;
        const t = typeof l.target === 'string' ? l.target : (l.target as Node).id;
        return s === d.id || t === d.id ? 2 : 1;
      });
      label.style('opacity', n => connected.has(n.id) ? 1 : 0.05);
    }).on('mouseleave', () => {
      setHovered(null);
      node.attr('fill-opacity', 0.85).attr('stroke-opacity', 0.3);
      link.attr('stroke-opacity', 0.4).attr('stroke-width', 1);
      label.style('opacity', 1);
    });

    simulation.on('tick', () => {
      link.attr('x1', d => (d.source as Node).x!).attr('y1', d => (d.source as Node).y!)
          .attr('x2', d => (d.target as Node).x!).attr('y2', d => (d.target as Node).y!);
      node.attr('cx', d => d.x!).attr('cy', d => d.y!);
      label.attr('x', d => d.x!).attr('y', d => d.y!);
    });

    return () => { simulation.stop(); };
  }, [articles, showLabels, selectedTag, lang, navigate]);

  if (loading) return <Loading text="Building graph..." />;

  return (
    <div className="h-full flex flex-col">
      {/* Controls */}
      <div className="flex items-center gap-3 p-4 border-b border-outline-variant/30 flex-wrap">
        <h1 className="font-headline text-xl font-bold">
          <Icon name="hub" className="text-primary mr-2 align-middle" />
          Knowledge Graph
        </h1>
        <div className="flex-1" />

        {/* Tag filter */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button
            onClick={() => setSelectedTag(null)}
            className={`px-2.5 py-1 rounded-full text-xs transition-colors ${
              !selectedTag ? 'bg-primary text-on-primary' : 'bg-surface-high text-on-surface-variant hover:bg-surface-highest'
            }`}>
            All
          </button>
          {allTags.slice(0, 8).map(t => (
            <button key={t} onClick={() => setSelectedTag(selectedTag === t ? null : t)}
              className={`px-2.5 py-1 rounded-full text-xs transition-colors ${
                selectedTag === t ? 'bg-primary text-on-primary' : 'bg-surface-high text-on-surface-variant hover:bg-surface-highest'
              }`}>
              {t}
            </button>
          ))}
        </div>

        <span className="text-sm text-on-surface-variant">
          {selectedTag ? articles.filter(a => a.tags?.includes(selectedTag)).length : articles.length} nodes
        </span>

        <label className="flex items-center gap-2 text-sm text-on-surface-variant cursor-pointer">
          <input type="checkbox" checked={showLabels} onChange={e => setShowLabels(e.target.checked)} className="rounded" />
          Labels
        </label>
      </div>

      {/* Graph + Info panel */}
      <div className="flex-1 relative flex">
        <svg ref={svgRef} className="flex-1 h-full" />

        {/* Hover info panel */}
        {hovered && (
          <div className="absolute bottom-4 left-4 bg-surface-container border border-outline-variant/40 rounded-xl p-4 max-w-[300px] shadow-lg card-shadow">
            <h3 className="font-headline font-semibold text-on-surface mb-1">{hovered.localTitle}</h3>
            {hovered.summary && (
              <p className="text-sm text-on-surface-variant mb-2 line-clamp-3">{hovered.summary}</p>
            )}
            <div className="flex items-center gap-3 text-xs text-outline">
              <span>{hovered.linkCount} connections</span>
              <span>{hovered.tags.slice(0, 3).join(', ')}</span>
            </div>
          </div>
        )}

        {articles.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-on-surface-variant">
            <div className="text-center">
              <Icon name="hub" className="text-5xl mb-3 block" />
              <p>No articles to visualize</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
