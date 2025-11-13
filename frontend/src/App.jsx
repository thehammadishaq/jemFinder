import { useState, useEffect } from 'react'
import CompanyProfile from './components/CompanyProfile'
import ProfileList from './components/ProfileList'
import { getAllProfiles, getProfileByTicker, searchProfiles, fetchProfileFromGemini, fetchProfileFromYFinance } from './services/api'

function App() {
  const [companyData, setCompanyData] = useState(null)
  const [currentTicker, setCurrentTicker] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [profiles, setProfiles] = useState([])
  const [showProfileList, setShowProfileList] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState('browse')
  const [profileTicker, setProfileTicker] = useState('')

  useEffect(() => {
    loadProfiles()
  }, [])

  const loadProfiles = async () => {
    try {
      setLoading(true)
      const data = await getAllProfiles()
      setProfiles(data.profiles || [])
    } catch (err) {
      console.error('Failed to load profiles:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleLoadByTicker = async (ticker) => {
    if (!ticker.trim()) {
      setError('Please enter a ticker symbol')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const profile = await getProfileByTicker(ticker.toUpperCase())
      setCompanyData(profile.data)
      setCurrentTicker(profile.ticker)
      setError(null)
    } catch (err) {
      setError(err.message || 'Profile not found')
      setCompanyData(null)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      await loadProfiles()
      return
    }

    setLoading(true)
    setError(null)

    try {
      const results = await searchProfiles(searchQuery)
      setProfiles(results)
    } catch (err) {
      setError(err.message || 'Search failed')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectProfile = (profile) => {
    setCompanyData(profile.data)
    setCurrentTicker(profile.ticker)
    setShowProfileList(false)
  }

  const handleDataUpdate = (updatedData) => {
    setCompanyData(updatedData)
  }

  const handleLoadProfile = async () => {
    if (!profileTicker.trim()) {
      setError('Please enter a ticker symbol')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const profile = await getProfileByTicker(profileTicker.toUpperCase())
      setCompanyData(profile.data)
      setCurrentTicker(profile.ticker)
      setError(null)
    } catch (err) {
      // If profile doesn't exist, create an empty profile structure
      // This allows users to fetch data from various sources
      const tickerUpper = profileTicker.toUpperCase()
      setCompanyData({}) // Empty data object
      setCurrentTicker(tickerUpper)
      setError(null) // Don't show error, show empty profile instead
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-black py-8 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-4xl font-bold text-black mb-2">Company Profile Dashboard</h1>
          <p className="text-lg text-black/70">View comprehensive company profile data from multiple sources</p>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white border border-black mb-8">
          <div className="border-b border-black flex">
            <button
              className={`flex-1 py-4 px-6 text-sm font-medium transition-colors ${
                viewMode === 'browse'
                  ? 'bg-black text-white'
                  : 'bg-white text-black hover:bg-black/5'
              }`}
              onClick={() => {
                setViewMode('browse')
                setShowProfileList(true)
                setCompanyData(null)
                setCurrentTicker(null)
                loadProfiles()
              }}
            >
              Browse
            </button>
            <button
              className={`flex-1 py-4 px-6 text-sm font-medium transition-colors border-l border-black ${
                viewMode === 'profile'
                  ? 'bg-black text-white'
                  : 'bg-white text-black hover:bg-black/5'
              }`}
              onClick={() => {
                setViewMode('profile')
                setShowProfileList(false)
              }}
            >
              Company Profile
            </button>
          </div>

          <div className="p-6">
            {viewMode === 'browse' && (
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Search by ticker..."
                  className="flex-1 py-3 px-4 border border-black focus:outline-none focus:ring-2 focus:ring-black"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleSearch()
                    }
                  }}
                />
                <button
                  className="px-6 py-3 bg-black text-white font-medium hover:bg-black/90 transition-colors disabled:bg-black/50"
                  onClick={handleSearch}
                  disabled={loading}
                >
                  Search
                </button>
                <button
                  className="px-6 py-3 border border-black text-black font-medium hover:bg-black hover:text-white transition-colors"
                  onClick={() => {
                    setSearchQuery('')
                    loadProfiles()
                  }}
                >
                  Clear
                </button>
              </div>
            )}

            {viewMode === 'profile' && (
              <div className="space-y-4">
                <div className="bg-black/5 border border-black p-4">
                  <p className="font-medium text-black mb-1">
                    Load company profile from database
                  </p>
                  <p className="text-sm text-black/70">
                    Enter a ticker to load existing profile or fetch from multiple data sources
                  </p>
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Enter ticker (e.g., AAPL, TSLA, MSFT)"
                    className="flex-1 py-3 px-4 border border-black focus:outline-none focus:ring-2 focus:ring-black uppercase"
                    value={profileTicker}
                    onChange={(e) => setProfileTicker(e.target.value.toUpperCase())}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter' && !loading) {
                        handleLoadProfile()
                      }
                    }}
                    disabled={loading}
                  />
                  <button
                    className="px-6 py-3 bg-black text-white font-medium hover:bg-black/90 transition-colors disabled:bg-black/50 disabled:cursor-not-allowed"
                    onClick={handleLoadProfile}
                    disabled={loading || !profileTicker.trim()}
                  >
                    {loading ? 'Loading...' : 'Load Profile'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-black text-white border border-black">
            <p className="font-medium">{error}</p>
          </div>
        )}

        {loading && !companyData && viewMode === 'browse' && (
          <div className="text-center py-12">
            <p className="text-lg text-black">Loading...</p>
          </div>
        )}


        {viewMode === 'browse' && showProfileList && (
          <ProfileList
            profiles={profiles}
            onSelectProfile={handleSelectProfile}
            loading={loading}
          />
        )}

        {companyData && (
          <CompanyProfile 
            data={companyData} 
            ticker={currentTicker} 
            onDataUpdate={handleDataUpdate}
          />
        )}

        {!companyData && !error && !loading && viewMode === 'profile' && (
          <div className="text-center py-12 border border-black bg-black/5">
            <p className="text-lg text-black mb-2">Enter a ticker symbol and click "Load Profile" to view company profile</p>
            <p className="text-sm text-black/70">You can fetch data from multiple sources (Gemini AI, Yahoo Finance) within the profile view</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
