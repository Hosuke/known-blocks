import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from '../components/Icon';
import { Shimmer } from '../components/Loading';
import { useLang } from '../lib/lang';
import { api } from '../lib/api';

type Tab = 'timeline' | 'people' | 'map';

interface Person { name: string; name_local?: string; dates?: string; role?: string; articles: string[] }
interface Event { name: string; name_local?: string; date?: string; description?: string; articles: string[] }
interface Place { name: string; name_local?: string; coords?: [number, number] | null; articles: string[] }

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

      {/* Timeline Tab */}
      {!loading && tab === 'timeline' && !isEmpty && (
        <div>
          {/* Filters */}
          <div className="flex gap-2 mb-6">
            {(['all', 'people', 'events'] as const).map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-3 py-1 text-xs rounded-full transition-colors ${
                  filter === f ? 'bg-primary/15 text-primary' : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-highest'
                }`}>
                {f === 'all' ? (zh ? '全部' : 'All') :
                 f === 'people' ? (zh ? '人物' : 'People') :
                 (zh ? '事件' : 'Events')}
              </button>
            ))}
          </div>

          {/* Timeline entries */}
          <div className="space-y-3">
            {(filter === 'all' || filter === 'people') && people.map((p, i) => (
              <div key={`p-${i}`} className="flex items-center gap-4 bg-surface-container rounded-xl p-4 border border-outline-variant/20 hover:border-primary/30 transition-colors cursor-pointer"
                onClick={() => p.articles[0] && navigate(`/wiki/${p.articles[0]}`)}>
                <div className="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{displayName(p)}</div>
                  <div className="text-xs text-on-surface-variant">{p.role}</div>
                </div>
                <div className="text-xs text-outline font-mono flex-shrink-0">{p.dates || '—'}</div>
                <span className="text-[10px] text-outline">{p.articles.length} {zh ? '篇' : 'articles'}</span>
              </div>
            ))}
            {(filter === 'all' || filter === 'events') && events.map((e, i) => (
              <div key={`e-${i}`} className="flex items-center gap-4 bg-surface-container rounded-xl p-4 border border-outline-variant/20 hover:border-secondary/30 transition-colors cursor-pointer"
                onClick={() => e.articles[0] && navigate(`/wiki/${e.articles[0]}`)}>
                <div className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{displayName(e)}</div>
                  <div className="text-xs text-on-surface-variant truncate">{e.description}</div>
                </div>
                <div className="text-xs text-outline font-mono flex-shrink-0">{e.date || '—'}</div>
              </div>
            ))}
          </div>
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
