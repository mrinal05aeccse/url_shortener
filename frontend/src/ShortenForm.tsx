import React, { useState } from 'react'

export default function ShortenForm(){
  const [target, setTarget] = useState('')
  const [result, setResult] = useState<any>(null)
  const backendOrigin = 'http://localhost:8000'

  async function submit(e: React.FormEvent){
    e.preventDefault()
    const resp = await fetch('/api/v1/shorten', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target })
    })
    const data = await resp.json()
    setResult(data)
  }

  return (
    <form onSubmit={submit} className="form">
      <input placeholder="https://example.com" value={target} onChange={e=>setTarget(e.target.value)} />
      <button type="submit">Shorten</button>
      {result && (
        <div className="result">
          Short URL: <a href={`${backendOrigin}/${result.alias}`} target="_blank" rel="noreferrer">{backendOrigin}/{result.alias}</a>
        </div>
      )}
    </form>
  )
}
