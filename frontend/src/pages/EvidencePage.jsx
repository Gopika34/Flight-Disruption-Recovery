import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, BookOpen, Scale, FileText, RefreshCw, AlertCircle, ExternalLink } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { searchPolicies } from '../services/api';

const QUICK_QUERIES = [
  'cancellation compensation',
  'flight delay meals hotel',
  'denied boarding overbooking',
  'involuntary downgrade',
  'extraordinary circumstances weather',
];

export function EvidencePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || 'cancellation compensation';

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const executeSearch = async (searchTerm) => {
    if (!searchTerm.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchPolicies(searchTerm.trim(), 6);
      setResults(data.results || []);
    } catch (err) {
      setError(err.message || 'Failed to retrieve DGCA policy clauses.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    executeSearch(initialQuery);
  }, []);

  const handleFormSubmit = (e) => {
    e.preventDefault();
    setSearchParams({ q: query });
    executeSearch(query);
  };

  const handleQuickClick = (q) => {
    setQuery(q);
    setSearchParams({ q });
    executeSearch(q);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-teal-400 font-mono text-xs">
          <Scale className="w-4 h-4" />
          <span>MongoDB Atlas Vector Search RAG Grounding</span>
        </div>
        <h1 className="text-xl sm:text-2xl font-extrabold text-white">
          DGCA Civil Aviation Requirements (CAR) Evidence
        </h1>
        <p className="text-xs text-slate-400">
          Official regulatory clauses from Section 3, Series M, Part IV: "Facilities to be provided to passengers by airlines due to denied boarding, cancellation of flights and delays in flights".
        </p>
      </div>

      {/* Search Input Bar */}
      <form onSubmit={handleFormSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
          <Input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search DGCA regulations (e.g. 3.4.1, meals, hotel, overbooking, weather)..."
            className="pl-10 text-xs font-mono"
          />
        </div>
        <Button type="submit" disabled={loading} size="default">
          {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Search Vector Index'}
        </Button>
      </form>

      {/* Quick Search Tags */}
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span className="text-slate-500 text-[11px] font-mono mr-1">Frequent:</span>
        {QUICK_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => handleQuickClick(q)}
            className="px-2.5 py-1 rounded-md text-[11px] font-mono bg-slate-900 border border-slate-800 text-slate-300 hover:border-teal-500/50 hover:text-white transition-colors cursor-pointer"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Error Notice */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results List */}
      <div className="space-y-4">
        {results.length === 0 && !loading && (
          <Card className="p-8 text-center text-xs text-slate-500">
            No policy clauses matched your search query. Try searching for terms like "cancellation", "delays", or "overbooking".
          </Card>
        )}

        {results.map((clause, idx) => (
          <Card key={clause.clause_id + idx} className="p-5 space-y-3 hover:border-slate-700 transition-colors">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
              <div className="flex items-center gap-2.5">
                <Badge variant="default" className="text-xs font-bold">
                  Para {clause.clause_id}
                </Badge>
                <span className="text-sm font-bold text-white">
                  {clause.section_title}
                </span>
              </div>
              <span className="text-[11px] font-mono text-slate-400">
                Official Gazetted Document · Page {clause.page_start}
              </span>
            </div>

            <p className="text-xs text-slate-200 leading-relaxed font-sans bg-[#070b14] p-4 rounded-lg border border-slate-850">
              "{clause.text}"
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
