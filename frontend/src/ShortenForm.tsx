import React, { useState } from 'react'

export default function ShortenForm(){
  const [target, setTarget] = useState('')
  const [result, setResult] = useState<any>(null)

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
          Short URL: <a href={`/${result.alias}`} target="_blank" rel="noreferrer">{window.location.origin}/{result.alias}</a>
        </div>
      )}
    </form>
  )
}
