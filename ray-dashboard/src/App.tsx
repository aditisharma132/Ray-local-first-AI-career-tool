import React, { useState } from 'react';
import { Compass, FileText, Globe, Loader2, Target, CheckCircle2, AlertTriangle, Zap, Building } from 'lucide-react';

interface AlignmentSummary {
  alignment_score: number;
  strong_matches: string[];
  partial_matches: string[];
  growth_opportunities: string[];
}

interface Strategy {
  candidate_archetype: string;
  persuasion_strategy: string;
  narrative_focus: string[];
}

function App() {
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jdUrl, setJdUrl] = useState('');
  const [companyUrl, setCompanyUrl] = useState('');
  const [tone, setTone] = useState('Strategic (Default)');

  const [isGenerating, setIsGenerating] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [coverLetter, setCoverLetter] = useState('');
  const [metrics, setMetrics] = useState<AlignmentSummary | null>(null);
  const [strategy, setStrategy] = useState<Strategy | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setResumeFile(e.target.files[0]);
    }
  };

  const handleGenerate = async () => {
    if (!resumeFile || !jdUrl || !companyUrl) {
      alert("Please provide all inputs.");
      return;
    }

    setIsGenerating(true);
    setCoverLetter('');
    setMetrics(null);
    setStrategy(null);
    setStatusMessage('Initializing Ray Intelligence Pipeline...');

    // Read the PDF file to send as base64 or binary later (simplification: we'll use REST for file upload, then WS for stream, but here we just simulate the WS payload if we convert PDF to text first. Wait, our FastAPI expects the text. Actually, our websocket endpoint in `main.py` expects `resume_text`.
    // We should probably convert PDF to text on backend. For this React prototype, let's just use the REST endpoint to upload the file and get the response, because sending a PDF via websocket requires base64 encoding or binary frames.
    // Wait, in `gateway/main.py`: `websocket.receive_json()` has `resume_text`. 
    // Let's use standard REST for now to ensure it works flawlessly, as the WS endpoint assumes frontend parsed the PDF. 

    const formData = new FormData();
    formData.append('resume', resumeFile);
    formData.append('jd_url', jdUrl);
    formData.append('company_url', companyUrl);
    formData.append('target_tone', tone);

    try {
      setStatusMessage('Extracting artifacts & formulating strategy...');
      const response = await fetch('http://localhost:8000/api/generate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setMetrics(data.alignment_summary);
      setStrategy(data.strategy);
      setCoverLetter(data.cover_letter);
      setStatusMessage('Strategy deployment complete.');
    } catch (error) {
      console.error(error);
      setStatusMessage('Analysis failed. Ensure FastAPI is running.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-200 font-sans p-6">
      <header className="max-w-6xl mx-auto mb-10 text-center">
        <div className="flex justify-center items-center gap-3 mb-2">
          <Compass className="w-10 h-10 text-emerald-500" />
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-emerald-400 to-cyan-500 text-transparent bg-clip-text">Ray</h1>
        </div>
        <p className="text-slate-400 tracking-widest uppercase text-sm font-semibold">Strategic Career Intelligence</p>
      </header>

      <main className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* Left Column: Inputs */}
        <section className="lg:col-span-4 bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2"><Target className="w-5 h-5 text-emerald-500" /> Candidate Vectors</h2>

          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Resume (PDF)</label>
              <input type="file" accept=".pdf" onChange={handleFileChange} className="block w-full text-sm text-slate-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-slate-800 file:text-emerald-400 hover:file:bg-slate-700 transition cursor-pointer bg-slate-950/50 rounded-lg border border-slate-800" />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Target Domain (Job URL)</label>
              <div className="relative">
                <Globe className="w-4 h-4 absolute left-3 top-3.5 text-slate-500" />
                <input type="text" value={jdUrl} onChange={e => setJdUrl(e.target.value)} placeholder="https://..." className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 pl-10 pr-4 focus:outline-none focus:border-emerald-500 transition text-sm text-slate-200 placeholder:text-slate-600" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Company Ontology (About URL)</label>
              <div className="relative">
                <Building className="w-4 h-4 absolute left-3 top-3.5 text-slate-500" />
                <input type="text" value={companyUrl} onChange={e => setCompanyUrl(e.target.value)} placeholder="https://..." className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 pl-10 pr-4 focus:outline-none focus:border-emerald-500 transition text-sm text-slate-200 placeholder:text-slate-600" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">Execution Persona</label>
              <select value={tone} onChange={e => setTone(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-lg py-3 px-4 focus:outline-none focus:border-emerald-500 transition text-sm text-slate-200 appearance-none">
                <option>Strategic (Default)</option>
                <option>Bold & Assertive</option>
                <option>Analytical Operator</option>
                <option>Research & Academic</option>
              </select>
            </div>

            <button
              onClick={handleGenerate}
              disabled={isGenerating}
              className="w-full mt-4 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isGenerating ? <Loader2 className="w-5 h-5 animate-spin" /> : <Zap className="w-5 h-5" />}
              {isGenerating ? 'Deploying Agents...' : 'Initialize Intelligence Engine'}
            </button>
          </div>
        </section>

        {/* Right Column: Output */}
        <section className="lg:col-span-8 flex flex-col gap-6">

          {/* Status Monitor */}
          {statusMessage && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center gap-3 text-emerald-400 text-sm font-mono animate-pulse">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span> {statusMessage}
            </div>
          )}

          {/* Metrics Dashboard */}
          {metrics && strategy && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl">
                <p className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Calculated Archetype</p>
                <p className="text-lg font-semibold text-emerald-300">{strategy.candidate_archetype}</p>
                <div className="mt-4 pt-4 border-t border-slate-800">
                  <p className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Persuasion Strategy Target</p>
                  <p className="text-sm text-slate-300">{strategy.persuasion_strategy}</p>
                </div>
              </div>

              <div className="bg-slate-900 border border-slate-800 p-5 rounded-xl flex flex-col justify-between">
                <div>
                  <p className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-1">Algorithmic Alignment</p>
                  <p className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">
                    {metrics.alignment_score}<span className="text-lg text-slate-500"> / 100</span>
                  </p>
                </div>

                <div className="mt-4 space-y-2">
                  <div className="flex items-start gap-2 text-sm text-emerald-400">
                    <CheckCircle2 className="w-4 h-4 mt-0.5" />
                    <span>{metrics.strong_matches[0] || 'No strong matches'}</span>
                  </div>
                  <div className="flex items-start gap-2 text-sm text-amber-400">
                    <AlertTriangle className="w-4 h-4 mt-0.5" />
                    <span>{metrics.growth_opportunities[0] || 'No specific gaps identified'}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Cover Letter Output */}
          {coverLetter && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl flex flex-col flex-grow min-h-[400px]">
              <div className="border-b border-slate-800 p-4 flex justify-between items-center bg-slate-950/30 rounded-t-xl">
                <h3 className="font-semibold flex items-center gap-2"><FileText className="w-4 h-4 text-emerald-500" /> Generated Strategy Artifact</h3>
                <button
                  onClick={() => {
                    const blob = new Blob([coverLetter], { type: 'text/plain' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'Ray_Strategy_Letter.txt';
                    a.click();
                  }}
                  className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 py-1.5 px-3 rounded transition"
                >
                  Download .TXT
                </button>
              </div>
              <textarea
                className="w-full h-full min-h-[400px] p-6 bg-transparent text-slate-300 focus:outline-none resize-none leading-relaxed"
                value={coverLetter}
                onChange={(e) => setCoverLetter(e.target.value)}
              />
            </div>
          )}

        </section>

      </main>
    </div>
  );
}

export default App;
