'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Mic2 } from 'lucide-react';

export default function Navbar() {
  const path = usePathname();
  const isHome = path === '/';

  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 32px',
        height: '64px',
        background: 'rgba(9,12,20,0.85)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      {/* Logo */}
      <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none' }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: 'linear-gradient(135deg, #4f9ef8 0%, #a78bfa 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 16px rgba(79,158,248,0.35)',
        }}>
          <Mic2 size={18} color="white" />
        </div>
        <span style={{
          fontFamily: "'Space Grotesk', sans-serif",
          fontWeight: 700, fontSize: 20, color: '#f0f4ff',
        }}>
          Whisper<span style={{ color: '#4f9ef8' }}>Score</span>
        </span>
      </Link>

      {/* Nav links */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Link href="/demo" style={{
          padding: '8px 18px', borderRadius: '8px',
          color: '#8b99b8', fontSize: '14px', fontWeight: 500,
          textDecoration: 'none', transition: 'color 0.2s',
        }}>
          Demo
        </Link>
        <Link href="/record" className="btn-primary" style={{ padding: '8px 20px', fontSize: '14px' }}>
          Start Recording
        </Link>
      </div>
    </nav>
  );
}
