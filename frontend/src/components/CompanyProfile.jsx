import { useState, useEffect, useRef } from 'react'
import SectionCard from './SectionCard'
import { fetchFundamentalsFromGemini, fetchProfileFromYFinance, fetchProfileFromGemini, fetchProfileFromPolygon, fetchDataFromFinnhub } from '../services/api'

function CompanyProfile({ data, ticker, onDataUpdate }) {
  const [activeDataSource, setActiveDataSource] = useState('Profile') // Profile, Gemini, YahooFinance, Polygon, Finnhub
  const [activeMainSection, setActiveMainSection] = useState('Identity')
  const [activeSubSection, setActiveSubSection] = useState('What')
  const lastLoadedTicker = useRef(null) // Track which ticker we last loaded sections for
  
  // Get localStorage key for this ticker
  const getStorageKey = (tickerValue) => `profileSections_${tickerValue?.toUpperCase() || 'default'}`
  
  // Load profile sections from localStorage
  const loadProfileSections = (tickerValue) => {
    if (!tickerValue) return []
    try {
      const stored = localStorage.getItem(getStorageKey(tickerValue))
      if (stored) {
        const parsed = JSON.parse(stored)
        return Array.isArray(parsed) ? parsed : []
      }
    } catch (error) {
      console.error('Error loading profile sections from localStorage:', error)
    }
    return []
  }
  
  const [profileSections, setProfileSections] = useState(() => loadProfileSections(ticker)) // Custom sections for Profile tab
  const [showAddSectionModal, setShowAddSectionModal] = useState(false)
  const [fundamentalsLoading, setFundamentalsLoading] = useState(false)
  const [fundamentalsStatus, setFundamentalsStatus] = useState('')
  const [fundamentalsError, setFundamentalsError] = useState(null)
  const [geminiLoading, setGeminiLoading] = useState(false)
  const [geminiStatus, setGeminiStatus] = useState('')
  const [geminiError, setGeminiError] = useState(null)
  const [yfinanceLoading, setYfinanceLoading] = useState(false)
  const [yfinanceStatus, setYfinanceStatus] = useState('')
  const [yfinanceError, setYfinanceError] = useState(null)
  const [polygonLoading, setPolygonLoading] = useState(false)
  const [polygonStatus, setPolygonStatus] = useState('')
  const [polygonError, setPolygonError] = useState(null)
  const [finnhubLoading, setFinnhubLoading] = useState(false)
  const [finnhubStatus, setFinnhubStatus] = useState('')
  const [finnhubError, setFinnhubError] = useState(null)

  // Determine available data sources
  const availableSources = []
  if (data?.Gemini) availableSources.push('Gemini')
  if (data?.YahooFinance) availableSources.push('YahooFinance')
  if (data?.Polygon) availableSources.push('Polygon')
  if (data?.Finnhub) availableSources.push('Finnhub')
  if (availableSources.length === 0) {
    // Default to Gemini if no data exists
    availableSources.push('Gemini')
  }

  // Get current source data
  const currentSourceData = data?.[activeDataSource] || {}

  // Get all available sections from all data sources for Profile tab
  const getAllAvailableSections = () => {
    const allSections = []
    
    // Get sections from each data source
    const sources = ['Gemini', 'YahooFinance', 'Polygon', 'Finnhub']
    
    sources.forEach(source => {
      const sourceData = data?.[source]
      if (!sourceData || typeof sourceData !== 'object') return
      
      // Handle Polygon, Finnhub, YahooFinance - direct keys
      if (source === 'Polygon' || source === 'Finnhub' || source === 'YahooFinance') {
        let apiData = sourceData
        if (sourceData.What && typeof sourceData.What === 'object') {
          apiData = sourceData.What
        }
        
        Object.keys(apiData).forEach(key => {
          if (key === 'What' || key === 'Sources' || key === 'When' || key === 'Where' || 
              key === 'How' || key === 'Who' || key === 'Why It Matters' || 
              key === '_metadata' || key.startsWith('_')) {
            return
          }
          
          const value = apiData[key]
          if (value !== null && value !== undefined && 
              (typeof value !== 'object' || Object.keys(value).length > 0)) {
            allSections.push({
              source,
              sectionKey: key,
              label: `${source === 'YahooFinance' ? 'Yahoo Finance' : source}: ${key}`,
              data: value
            })
          }
        })
      } else if (source === 'Gemini') {
        // Handle Gemini - structured sections
        const identitySubSections = ['What', 'When', 'Where', 'How', 'Who', 'Sources']
        identitySubSections.forEach(subSection => {
          const sectionData = sourceData[subSection]
          if (sectionData && typeof sectionData === 'object' && Object.keys(sectionData).length > 0) {
            allSections.push({
              source,
              sectionKey: `Identity.${subSection}`,
              label: `${source}: Identity - ${subSection}`,
              data: sectionData
            })
          }
        })
        
        // Other Gemini sections
        const otherSections = ['Ratings', 'News', 'Developments', 'Events', 'Catalyst', 'StockBehaviour', 'Stock Behaviour']
        otherSections.forEach(sectionKey => {
          const sectionData = sourceData[sectionKey] || sourceData[sectionKey.toLowerCase()]
          if (sectionData && typeof sectionData === 'object' && Object.keys(sectionData).length > 0) {
            allSections.push({
              source,
              sectionKey,
              label: `${source}: ${sectionKey}`,
              data: sectionData
            })
          }
        })
      }
    })
    
    return allSections
  }

  // Save profile sections to localStorage whenever they change
  useEffect(() => {
    if (ticker && profileSections.length >= 0) {
      try {
        // Save only the metadata (source, sectionKey, label) not the full data
        // We'll sync data when loading
        const sectionsToSave = profileSections.map(s => ({
          source: s.source,
          sectionKey: s.sectionKey,
          label: s.label
        }))
        localStorage.setItem(getStorageKey(ticker), JSON.stringify(sectionsToSave))
      } catch (error) {
        console.error('Error saving profile sections to localStorage:', error)
      }
    }
  }, [profileSections, ticker])

  // Load profile sections when ticker changes
  useEffect(() => {
    if (ticker && lastLoadedTicker.current !== ticker) {
      lastLoadedTicker.current = ticker
      const loaded = loadProfileSections(ticker)
      if (loaded.length > 0) {
        // Sync loaded sections with current data (keep sections even if data not available yet)
        const syncedSections = loaded.map(savedSection => {
          const sourceData = data?.[savedSection.source]
          
          // Get the actual data for this section
          let sectionData = null
          
          if (sourceData) {
            if (savedSection.source === 'Polygon' || savedSection.source === 'Finnhub' || savedSection.source === 'YahooFinance') {
              let apiData = sourceData
              if (sourceData.What && typeof sourceData.What === 'object') {
                apiData = sourceData.What
              }
              sectionData = apiData[savedSection.sectionKey]
            } else if (savedSection.source === 'Gemini') {
              if (savedSection.sectionKey.startsWith('Identity.')) {
                const subSection = savedSection.sectionKey.split('.')[1]
                sectionData = sourceData[subSection]
              } else {
                sectionData = sourceData[savedSection.sectionKey] || sourceData[savedSection.sectionKey.toLowerCase()]
              }
            }
          }
          
          // Return section with data if available, otherwise return section with empty data
          return {
            ...savedSection,
            data: (sectionData && typeof sectionData === 'object' && Object.keys(sectionData).length > 0) ? sectionData : {}
          }
        })
        
        setProfileSections(syncedSections)
      } else {
        setProfileSections([])
      }
    } else if (!ticker) {
      lastLoadedTicker.current = null
      setProfileSections([])
    }
  }, [ticker]) // Only run when ticker changes

  // Update section data when data changes (but keep the section list)
  useEffect(() => {
    if (ticker && profileSections.length > 0) {
      setProfileSections(prevSections => {
        return prevSections.map(savedSection => {
          const sourceData = data?.[savedSection.source]
          if (!sourceData) return savedSection // Keep section even if data not available yet
          
          // Get the actual data for this section
          let sectionData = null
          
          if (savedSection.source === 'Polygon' || savedSection.source === 'Finnhub' || savedSection.source === 'YahooFinance') {
            let apiData = sourceData
            if (sourceData.What && typeof sourceData.What === 'object') {
              apiData = sourceData.What
            }
            sectionData = apiData[savedSection.sectionKey]
          } else if (savedSection.source === 'Gemini') {
            if (savedSection.sectionKey.startsWith('Identity.')) {
              const subSection = savedSection.sectionKey.split('.')[1]
              sectionData = sourceData[subSection]
            } else {
              sectionData = sourceData[savedSection.sectionKey] || sourceData[savedSection.sectionKey.toLowerCase()]
            }
          }
          
          // Update data if available, otherwise keep existing
          if (sectionData && typeof sectionData === 'object' && Object.keys(sectionData).length > 0) {
            return {
              ...savedSection,
              data: sectionData
            }
          }
          return savedSection // Keep section with existing data
        })
      })
    }
  }, [data]) // Update data when data changes

  // Handle adding section to Profile tab
  const handleAddSection = (section) => {
    // Check if section already exists
    const exists = profileSections.some(s => 
      s.source === section.source && s.sectionKey === section.sectionKey
    )
    
    if (!exists) {
      setProfileSections([...profileSections, section])
    }
    setShowAddSectionModal(false)
  }

  // Handle removing section from Profile tab
  const handleRemoveSection = (index) => {
    setProfileSections(profileSections.filter((_, i) => i !== index))
  }

  // Identity sub-sections (moved from top tabs)
  const identitySections = {
    What: currentSourceData.What || {},
    When: currentSourceData.When || {},
    Where: currentSourceData.Where || {},
    How: currentSourceData.How || {},
    Who: currentSourceData.Who || {},
    Sources: currentSourceData.Sources || {}
  }

  // Helper function to check if a section has data
  const hasSectionData = (sectionKey) => {
    // Skip Identity check for Polygon, Finnhub, and Yahoo Finance - they use different structure
    if (activeDataSource === 'Polygon' || activeDataSource === 'Finnhub' || activeDataSource === 'YahooFinance') {
      return false
    }
    
    if (sectionKey === 'Identity') {
      // Check if any identity sub-section has data
      return Object.values(identitySections).some(section => 
        section && typeof section === 'object' && Object.keys(section).length > 0
      )
    }
    
    // Check various possible keys for each section
    const sectionChecks = {
      Fundamentals: () => {
        const fundamentals = data?.Fundamentals || data?.fundamentals || currentSourceData.Fundamentals || currentSourceData.fundamentals || {}
        return fundamentals && typeof fundamentals === 'object' && Object.keys(fundamentals).length > 0
      },
      Ratings: () => {
        const ratings = currentSourceData.Ratings || currentSourceData.ratings || {}
        return ratings && typeof ratings === 'object' && Object.keys(ratings).length > 0
      },
      News: () => {
        const news = currentSourceData.News || currentSourceData.news || {}
        return news && typeof news === 'object' && Object.keys(news).length > 0
      },
      Developments: () => {
        const developments = currentSourceData.Developments || currentSourceData.Events || currentSourceData.Catalyst || 
                            currentSourceData.developments || currentSourceData.events || currentSourceData.catalyst || {}
        return developments && typeof developments === 'object' && Object.keys(developments).length > 0
      },
      StockBehaviour: () => {
        const stockBehaviour = currentSourceData.StockBehaviour || currentSourceData['Stock Behaviour'] || 
                              currentSourceData.stockBehaviour || currentSourceData['stock behaviour'] || {}
        return stockBehaviour && typeof stockBehaviour === 'object' && Object.keys(stockBehaviour).length > 0
      }
    }
    
    return sectionChecks[sectionKey] ? sectionChecks[sectionKey]() : false
  }

  // Dynamically build sidebar sections based on available data
  const buildSidebarSections = () => {
    const sections = []
    
    // Special handling for Polygon.io, Finnhub, and Yahoo Finance - create buttons from JSON keys
    if ((activeDataSource === 'Polygon' || activeDataSource === 'Finnhub' || activeDataSource === 'YahooFinance') && currentSourceData && typeof currentSourceData === 'object') {
      // Handle both old structure (wrapped in "What") and new structure (direct keys)
      let apiData = currentSourceData
      
      // If data is wrapped in "What" key (old structure), extract it
      if (currentSourceData.What && typeof currentSourceData.What === 'object') {
        apiData = currentSourceData.What
      }
      
      // Get all top-level keys from API data, excluding wrapper keys and metadata
      const apiKeys = Object.keys(apiData).filter(key => {
        // Skip Identity wrapper keys
        if (key === 'What' || key === 'Sources' || key === 'When' || key === 'Where' || key === 'How' || key === 'Who' || key === 'Why It Matters') {
          return false
        }
        // Skip metadata keys
        if (key === '_metadata' || key.startsWith('_')) {
          return false
        }
        const value = apiData[key]
        // Only include keys that have actual data (not null, not empty object)
        return value !== null && 
               value !== undefined && 
               (typeof value !== 'object' || Object.keys(value).length > 0)
      })
      
      // Create sections from API keys
      apiKeys.forEach(key => {
        sections.push({ 
          key: key, 
          label: key, 
          hasSubSections: false 
        })
      })
      
      return sections
    }
    
    // For Gemini data source, check for What/When/Where/How/Who structure
    if (activeDataSource === 'Gemini' && currentSourceData && typeof currentSourceData === 'object') {
      const geminiSections = ['What', 'When', 'Where', 'How', 'Who', 'Sources']
      geminiSections.forEach(sectionKey => {
        if (currentSourceData[sectionKey] && 
            typeof currentSourceData[sectionKey] === 'object' && 
            Object.keys(currentSourceData[sectionKey]).length > 0) {
          sections.push({ 
            key: sectionKey, 
            label: sectionKey, 
            hasSubSections: false 
          })
        }
      })
      return sections
    }
    
    // For other data sources, use existing logic
    // Always check for Identity first (if any sub-section has data)
    if (hasSectionData('Identity')) {
      sections.push({ key: 'Identity', label: 'Identity', hasSubSections: true })
    }
    
    // Check for other sections in order
    const sectionConfigs = [
    { key: 'Fundamentals', label: 'Fundamentals', hasSubSections: false },
    { key: 'Ratings', label: 'Ratings', hasSubSections: false },
    { key: 'News', label: 'News', hasSubSections: false },
    { key: 'Developments', label: 'Developments / Events / Catalyst', hasSubSections: false },
    { key: 'StockBehaviour', label: 'Stock Behaviour', hasSubSections: false }
  ]
    
    sectionConfigs.forEach(config => {
      if (hasSectionData(config.key)) {
        sections.push(config)
      }
    })
    
    return sections
  }

  // Main sections configuration - dynamically built from JSON data
  const sidebarSections = buildSidebarSections()

  // Set default active source if current one doesn't exist (but not for Profile tab)
  useEffect(() => {
    if (activeDataSource !== 'Profile' && !data?.[activeDataSource] && availableSources.length > 0) {
      setActiveDataSource(availableSources[0])
    }
  }, [data, activeDataSource, availableSources])

  // Reset active section when switching to Polygon, Finnhub, or Yahoo Finance data source
  useEffect(() => {
    if ((activeDataSource === 'Polygon' || activeDataSource === 'Finnhub' || activeDataSource === 'YahooFinance') && currentSourceData && typeof currentSourceData === 'object') {
      // Handle both old structure (wrapped in "What") and new structure (direct keys)
      let apiData = currentSourceData
      
      // If data is wrapped in "What" key (old structure), extract it
      if (currentSourceData.What && typeof currentSourceData.What === 'object') {
        apiData = currentSourceData.What
      }
      
      const apiKeys = Object.keys(apiData).filter(key => {
        // Skip Identity wrapper keys
        if (key === 'What' || key === 'Sources' || key === 'When' || key === 'Where' || key === 'How' || key === 'Who' || key === 'Why It Matters') {
          return false
        }
        // Skip metadata keys
        if (key === '_metadata' || key.startsWith('_')) {
          return false
        }
        const value = apiData[key]
        return value !== null && 
               value !== undefined && 
               (typeof value !== 'object' || Object.keys(value).length > 0)
      })
      
      // If current section is not a valid API key, set to first available
      if (apiKeys.length > 0 && !apiKeys.includes(activeMainSection)) {
        setActiveMainSection(apiKeys[0])
      }
    }
  }, [activeDataSource, currentSourceData, activeMainSection])

  // Reset active section if current section is no longer available (but not for Profile tab)
  useEffect(() => {
    if (activeDataSource === 'Profile') return // Skip for Profile tab
    
    const availableSections = buildSidebarSections()
    const currentSectionExists = availableSections.some(s => s.key === activeMainSection)
    
    if (!currentSectionExists && availableSections.length > 0) {
      // Set to first available section
      const firstSection = availableSections[0]
      setActiveMainSection(firstSection.key)
      
      // Only handle Identity sub-sections for non-Polygon/Finnhub/YahooFinance sources
      if (activeDataSource !== 'Polygon' && activeDataSource !== 'Finnhub' && activeDataSource !== 'YahooFinance' && firstSection.key === 'Identity') {
        // Find first available identity sub-section
        const availableSubSections = Object.keys(identitySections).filter(key => {
          const section = identitySections[key]
          return section && typeof section === 'object' && Object.keys(section).length > 0
        })
        if (availableSubSections.length > 0) {
          setActiveSubSection(availableSubSections[0])
        }
      }
    }
  }, [currentSourceData, activeMainSection, identitySections, activeDataSource])

  // Handle Profile tab section selection
  useEffect(() => {
    if (activeDataSource === 'Profile') {
      if (profileSections.length > 0) {
        const currentSectionExists = profileSections.some(s => 
          `${s.source}-${s.sectionKey}` === activeMainSection
        )
        if (!currentSectionExists) {
          setActiveMainSection(`${profileSections[0].source}-${profileSections[0].sectionKey}`)
        }
      } else {
        setActiveMainSection('')
      }
    }
  }, [activeDataSource, profileSections, activeMainSection])

  // Get data for current section
  const getSectionData = () => {
    // Handle Profile tab - get data from profileSections
    if (activeDataSource === 'Profile') {
      const selectedSection = profileSections.find(s => 
        `${s.source}-${s.sectionKey}` === activeMainSection
      )
      return selectedSection ? selectedSection.data : {}
    }
    
    // Special handling for Gemini - return data directly from What/When/Where/How/Who/Sources keys
    if (activeDataSource === 'Gemini' && currentSourceData) {
      if (currentSourceData[activeMainSection] && 
          typeof currentSourceData[activeMainSection] === 'object') {
        return currentSourceData[activeMainSection] || {}
      }
      return {}
    }
    
    // Special handling for Polygon.io, Finnhub, and Yahoo Finance - return data directly from the key
    if ((activeDataSource === 'Polygon' || activeDataSource === 'Finnhub' || activeDataSource === 'YahooFinance') && currentSourceData) {
      // Handle both old structure (wrapped in "What") and new structure (direct keys)
      let apiData = currentSourceData
      
      // If data is wrapped in "What" key (old structure), extract it
      if (currentSourceData.What && typeof currentSourceData.What === 'object') {
        apiData = currentSourceData.What
      }
      
      return apiData[activeMainSection] || {}
    }
    
    // For other sources, handle Identity sub-sections
    if (activeMainSection === 'Identity') {
      return identitySections[activeSubSection] || {}
    }
    
    // Try multiple possible keys for each section
    const sectionMap = {
      Fundamentals: data?.Fundamentals || data?.fundamentals || {},
      Ratings: currentSourceData.Ratings || currentSourceData.ratings || {},
      News: currentSourceData.News || currentSourceData.news || {},
      Developments: currentSourceData.Developments || currentSourceData.Events || currentSourceData.Catalyst || currentSourceData.developments || currentSourceData.events || currentSourceData.catalyst || {},
      StockBehaviour: currentSourceData.StockBehaviour || currentSourceData['Stock Behaviour'] || currentSourceData.stockBehaviour || currentSourceData['stock behaviour'] || {}
    }
    
    return sectionMap[activeMainSection] || {}
  }

  const getSectionTitle = () => {
    // Handle Profile tab
    if (activeDataSource === 'Profile') {
      const selectedSection = profileSections.find(s => 
        `${s.source}-${s.sectionKey}` === activeMainSection
      )
      return selectedSection ? selectedSection.label : 'Select a section'
    }
    
    // For Polygon.io, Finnhub, and Yahoo Finance, use the section key directly as the title
    if (activeDataSource === 'Polygon' || activeDataSource === 'Finnhub' || activeDataSource === 'YahooFinance') {
      return activeMainSection
    }
    
    if (activeMainSection === 'Identity') {
      return activeSubSection
    }
    return sidebarSections.find(s => s.key === activeMainSection)?.label || activeMainSection
  }

  const handleFetchFundamentals = async () => {
    if (!ticker) {
      setFundamentalsError('Ticker symbol is required')
      return
    }

    setFundamentalsLoading(true)
    setFundamentalsError(null)
    setFundamentalsStatus('Opening Gemini browser...')

    try {
      setFundamentalsStatus('Sending query to Gemini AI...')
      const result = await fetchFundamentalsFromGemini(ticker.toUpperCase(), true)
      
      setFundamentalsStatus('Fundamentals fetched successfully!')
      
      // Merge fundamentals data into existing data
      if (onDataUpdate && result.data) {
        const updatedData = {
          ...data,
          Fundamentals: result.data
        }
        onDataUpdate(updatedData)
      }
      
      setFundamentalsError(null)
      
      setTimeout(() => {
        setFundamentalsStatus('')
      }, 3000)
    } catch (err) {
      const errorMsg = err.message || 'Failed to fetch fundamentals from Gemini'
      setFundamentalsError(errorMsg)
      setFundamentalsStatus('Failed to fetch fundamentals')
      setTimeout(() => {
        setFundamentalsStatus('')
      }, 5000)
    } finally {
      setFundamentalsLoading(false)
    }
  }

  const handleFetchGemini = async () => {
    if (!ticker) {
      setGeminiError('Ticker symbol is required')
      return
    }

    setGeminiLoading(true)
    setGeminiError(null)
    setGeminiStatus('Opening Gemini browser...')

    try {
      setGeminiStatus('Sending query to Gemini AI...')
      const result = await fetchProfileFromGemini(ticker.toUpperCase(), true)
      
      setGeminiStatus('Profile fetched successfully from Gemini!')
      
      // Save Gemini data separately under "Gemini" key
      if (onDataUpdate && result.data) {
        const updatedData = {
          ...data,
          Gemini: result.data  // Save separately by source
        }
        onDataUpdate(updatedData)
        // Switch to Gemini source after fetching
        setActiveDataSource('Gemini')
      }
      
      setGeminiError(null)
      
      setTimeout(() => {
        setGeminiStatus('')
      }, 3000)
    } catch (err) {
      const errorMsg = err.message || 'Failed to fetch profile from Gemini'
      setGeminiError(errorMsg)
      setGeminiStatus('Failed to fetch profile')
      setTimeout(() => {
        setGeminiStatus('')
      }, 5000)
    } finally {
      setGeminiLoading(false)
    }
  }

  const handleFetchYFinance = async () => {
    if (!ticker) {
      setYfinanceError('Ticker symbol is required')
      return
    }

    setYfinanceLoading(true)
    setYfinanceError(null)
    setYfinanceStatus('Fetching from Yahoo Finance...')

    try {
      setYfinanceStatus('Fetching company profile data from Yahoo Finance...')
      
      // Use backend API (similar to Polygon and Finnhub)
      const result = await fetchProfileFromYFinance(ticker.toUpperCase(), true)
      
      setYfinanceStatus('Profile fetched successfully from Yahoo Finance!')
      
      // Save Yahoo Finance data separately under "YahooFinance" key
      if (onDataUpdate && result.data) {
        const updatedData = {
          ...data,
          YahooFinance: result.data  // Save separately by source
        }
        
        onDataUpdate(updatedData)
        // Switch to Yahoo Finance source after fetching
        setActiveDataSource('YahooFinance')
      }
      
      setYfinanceError(null)
      
      setTimeout(() => {
        setYfinanceStatus('')
      }, 3000)
    } catch (err) {
      const errorMsg = err.message || 'Failed to fetch profile from Yahoo Finance'
      setYfinanceError(errorMsg)
      setYfinanceStatus('Failed to fetch profile')
      setTimeout(() => {
        setYfinanceStatus('')
      }, 5000)
    } finally {
      setYfinanceLoading(false)
    }
  }

  const handleFetchPolygon = async () => {
    if (!ticker) {
      setPolygonError('Ticker symbol is required')
      return
    }

    setPolygonLoading(true)
    setPolygonError(null)
    setPolygonStatus('Fetching from Polygon.io...')

    try {
      setPolygonStatus('Fetching company profile data...')
      const result = await fetchProfileFromPolygon(ticker.toUpperCase(), true)
      
      setPolygonStatus('Profile fetched successfully from Polygon.io!')
      
      // Save Polygon data separately under "Polygon" key
      if (onDataUpdate && result.data) {
        const updatedData = {
          ...data,
          Polygon: result.data  // Save separately by source
        }
        onDataUpdate(updatedData)
        // Switch to Polygon source after fetching
        setActiveDataSource('Polygon')
      }
      
      setPolygonError(null)
      
      setTimeout(() => {
        setPolygonStatus('')
      }, 3000)
    } catch (err) {
      const errorMsg = err.message || 'Failed to fetch profile from Polygon.io'
      setPolygonError(errorMsg)
      setPolygonStatus('Failed to fetch profile')
      setTimeout(() => {
        setPolygonStatus('')
      }, 5000)
      } finally {
        setPolygonLoading(false)
      }
    }

    const handleFetchFinnhub = async () => {
      if (!ticker) {
        setFinnhubError('Ticker symbol is required')
        return
      }

      setFinnhubLoading(true)
      setFinnhubError(null)
      setFinnhubStatus('Fetching from Finnhub...')

      try {
        setFinnhubStatus('Fetching company data...')
        const result = await fetchDataFromFinnhub(ticker.toUpperCase(), true)
        
        setFinnhubStatus('Data fetched successfully from Finnhub!')
        
        // Save Finnhub data separately under "Finnhub" key
        if (onDataUpdate && result.data) {
          const updatedData = {
            ...data,
            Finnhub: result.data  // Save separately by source
          }
          onDataUpdate(updatedData)
          // Switch to Finnhub source after fetching
          setActiveDataSource('Finnhub')
        }
        
        setFinnhubError(null)
        
        setTimeout(() => {
          setFinnhubStatus('')
        }, 3000)
      } catch (err) {
        const errorMsg = err.message || 'Failed to fetch data from Finnhub'
        setFinnhubError(errorMsg)
        setFinnhubStatus('Failed to fetch data')
        setTimeout(() => {
          setFinnhubStatus('')
        }, 5000)
      } finally {
        setFinnhubLoading(false)
      }
    }

  // Check if this is a completely new/empty profile
  const isNewProfile = !data || Object.keys(data).length === 0

  return (
    <div className="mt-8 border border-black bg-white">
      <div className="border-b border-black px-6 py-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-black">
            Company Profile{ticker ? `: ${ticker}` : ''}
          </h2>
        </div>
      </div>

      {/* Welcome message for new profiles */}
      {isNewProfile && (
        <div className="border-b border-black bg-black/5 px-6 py-4">
          <div className="max-w-3xl">
            <p className="text-base font-medium text-black mb-2">
              Welcome! This is a new profile for <strong>{ticker}</strong>.
            </p>
            <p className="text-sm text-black/70 mb-3">
              Get started by fetching data from any of the sources below. You can fetch from multiple sources and they'll all be saved to this profile.
            </p>
            <div className="flex flex-wrap gap-2 text-xs text-black/60">
              <span>💡 <strong>Tip:</strong> Start with Yahoo Finance (fastest) or Polygon.io for quick data</span>
            </div>
          </div>
        </div>
      )}

      {/* Data Sources Tab Bar */}
      <div className="border-b border-black bg-white">
        <div className="flex">
          <button
            className={`px-6 py-3 text-sm font-medium transition-colors border-r border-black ${
              activeDataSource === 'Profile'
                ? 'bg-black text-white'
                : 'bg-white text-black hover:bg-black/5'
            }`}
            onClick={() => setActiveDataSource('Profile')}
          >
            Profile
          </button>
          <button
            className={`px-6 py-3 text-sm font-medium transition-colors border-r border-black ${
              activeDataSource === 'Gemini'
                ? 'bg-black text-white'
                : 'bg-white text-black hover:bg-black/5'
            } ${!data?.Gemini ? 'opacity-60' : ''}`}
            onClick={() => setActiveDataSource('Gemini')}
          >
            Gemini AI
            {data?.Gemini && <span className="ml-2 text-xs">●</span>}
          </button>
          <button
            className={`px-6 py-3 text-sm font-medium transition-colors border-r border-black ${
              activeDataSource === 'YahooFinance'
                ? 'bg-black text-white'
                : 'bg-white text-black hover:bg-black/5'
            } ${!data?.YahooFinance ? 'opacity-60' : ''}`}
            onClick={() => setActiveDataSource('YahooFinance')}
          >
            Yahoo Finance
            {data?.YahooFinance && <span className="ml-2 text-xs">●</span>}
          </button>
              <button
                className={`px-6 py-3 text-sm font-medium transition-colors border-r border-black ${
                  activeDataSource === 'Polygon'
                    ? 'bg-black text-white'
                    : 'bg-white text-black hover:bg-black/5'
                } ${!data?.Polygon ? 'opacity-60' : ''}`}
                onClick={() => setActiveDataSource('Polygon')}
              >
                Polygon.io
                {data?.Polygon && <span className="ml-2 text-xs">●</span>}
              </button>
              <button
                className={`px-6 py-3 text-sm font-medium transition-colors ${
                  activeDataSource === 'Finnhub'
                    ? 'bg-black text-white'
                    : 'bg-white text-black hover:bg-black/5'
                } ${!data?.Finnhub ? 'opacity-60' : ''}`}
                onClick={() => setActiveDataSource('Finnhub')}
              >
                Finnhub
                {data?.Finnhub && <span className="ml-2 text-xs">●</span>}
              </button>
            </div>
          </div>

      {/* Fetch Buttons for Data Sources */}
      <div className="border-b border-black bg-black/5 px-6 py-4">
        <div className="grid grid-cols-4 gap-4">
          {/* Gemini AI */}
          <div className="flex flex-col">
            <div className="flex items-start justify-between gap-3 mb-1">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-black">Gemini AI</p>
                <p className="text-xs text-black/70">Browser automation (30-60 seconds)</p>
              </div>
              <button
                className="px-4 py-2 bg-black text-white text-xs font-medium hover:bg-black/90 transition-colors disabled:bg-black/50 disabled:cursor-not-allowed flex-shrink-0"
                onClick={handleFetchGemini}
                disabled={geminiLoading || !ticker}
              >
                {geminiLoading ? 'Fetching...' : 'Fetch'}
              </button>
            </div>
            {geminiStatus && (
              <p className="text-xs text-black/70 mt-1">{geminiStatus}</p>
            )}
            {geminiError && (
              <p className="text-xs text-red-600 mt-1">{geminiError}</p>
            )}
          </div>
          
          {/* Yahoo Finance */}
          <div className="flex flex-col border-l border-black/20 pl-4">
            <div className="flex items-start justify-between gap-3 mb-1">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-black">Yahoo Finance</p>
                <p className="text-xs text-black/70">Backend API (3-8 seconds)</p>
              </div>
              <button
                className="px-4 py-2 bg-black text-white text-xs font-medium hover:bg-black/90 transition-colors disabled:bg-black/50 disabled:cursor-not-allowed flex-shrink-0"
                onClick={handleFetchYFinance}
                disabled={yfinanceLoading || !ticker}
              >
                {yfinanceLoading ? 'Fetching...' : 'Fetch'}
              </button>
            </div>
            {yfinanceStatus && (
              <p className="text-xs text-black/70 mt-1">{yfinanceStatus}</p>
            )}
            {yfinanceError && (
              <p className="text-xs text-red-600 mt-1">{yfinanceError}</p>
            )}
          </div>
          
          {/* Polygon.io */}
          <div className="flex flex-col border-l border-black/20 pl-4">
            <div className="flex items-start justify-between gap-3 mb-1">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-black">Polygon.io</p>
                <p className="text-xs text-black/70">Fast API (2-5 seconds)</p>
              </div>
              <button
                className="px-4 py-2 bg-black text-white text-xs font-medium hover:bg-black/90 transition-colors disabled:bg-black/50 disabled:cursor-not-allowed flex-shrink-0"
                onClick={handleFetchPolygon}
                disabled={polygonLoading || !ticker}
              >
                {polygonLoading ? 'Fetching...' : 'Fetch'}
              </button>
            </div>
            {polygonStatus && (
              <p className="text-xs text-black/70 mt-1">{polygonStatus}</p>
            )}
            {polygonError && (
              <p className="text-xs text-red-600 mt-1">{polygonError}</p>
            )}
          </div>
          
          {/* Finnhub */}
          <div className="flex flex-col border-l border-black/20 pl-4">
            <div className="flex items-start justify-between gap-3 mb-1">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-black">Finnhub</p>
                <p className="text-xs text-black/70">Fast API (3-8 seconds)</p>
              </div>
              <button
                className="px-4 py-2 bg-black text-white text-xs font-medium hover:bg-black/90 transition-colors disabled:bg-black/50 disabled:cursor-not-allowed flex-shrink-0"
                onClick={handleFetchFinnhub}
                disabled={finnhubLoading || !ticker}
              >
                {finnhubLoading ? 'Fetching...' : 'Fetch'}
              </button>
            </div>
            {finnhubStatus && (
              <p className="text-xs text-black/70 mt-1">{finnhubStatus}</p>
            )}
            {finnhubError && (
              <p className="text-xs text-red-600 mt-1">{finnhubError}</p>
            )}
          </div>
        </div>
      </div>

      <div className="flex min-h-[600px]">
        {/* Left Sidebar */}
        <div className="w-72 border-r border-black bg-white flex-shrink-0">
          <nav className="py-4">
            {/* Profile Tab Sidebar */}
            {activeDataSource === 'Profile' ? (
              <>
                <div className="px-6 py-3 border-b border-black">
                  <button
                    className="w-full px-4 py-2 bg-black text-white text-sm font-medium hover:bg-black/90 transition-colors"
                    onClick={() => setShowAddSectionModal(true)}
                  >
                    + Add Section
                  </button>
                </div>
                {profileSections.length === 0 ? (
                  <div className="px-6 py-4 text-sm text-black/70">
                    No sections added. Click "Add Section" to add sections from any data source.
                  </div>
                ) : (
                  profileSections.map((section, index) => (
                    <div key={`${section.source}-${section.sectionKey}-${index}`}>
                      <div className="flex items-center justify-between border-b border-black">
                        <button
                          className={`flex-1 text-left px-6 py-3 text-sm font-medium transition-colors ${
                            activeMainSection === `${section.source}-${section.sectionKey}`
                              ? 'bg-black text-white'
                              : 'bg-white text-black hover:bg-black/5'
                          }`}
                          onClick={() => setActiveMainSection(`${section.source}-${section.sectionKey}`)}
                        >
                          {section.label}
                        </button>
                        <button
                          className="px-3 py-3 text-red-600 hover:bg-red-50 transition-colors"
                          onClick={() => handleRemoveSection(index)}
                          title="Remove section"
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </>
            ) : sidebarSections.length === 0 ? (
              <div className="px-6 py-4 text-sm text-black/70">
                No sections available. Fetch data from a source above.
              </div>
            ) : (
              sidebarSections.map((section) => (
              <div key={section.key}>
                <button
                  className={`w-full text-left px-6 py-3 text-sm font-medium transition-colors border-b border-black ${
                    activeMainSection === section.key
                      ? 'bg-black text-white'
                      : 'bg-white text-black hover:bg-black/5'
                  }`}
                  onClick={() => {
                    setActiveMainSection(section.key)
                    // Only handle Identity sub-sections for non-Polygon/Finnhub/YahooFinance sources
                    if (activeDataSource !== 'Polygon' && activeDataSource !== 'Finnhub' && activeDataSource !== 'YahooFinance' && section.key === 'Identity') {
                      // Find first available identity sub-section
                      const availableSubSections = Object.keys(identitySections).filter(key => {
                        const sectionData = identitySections[key]
                        return sectionData && typeof sectionData === 'object' && Object.keys(sectionData).length > 0
                      })
                      if (availableSubSections.length > 0) {
                        setActiveSubSection(availableSubSections[0])
                      }
                    }
                  }}
                >
                  {section.label}
                </button>

                {/* Sub-sections for Identity (only for non-Polygon/Finnhub/YahooFinance sources) */}
                {activeDataSource !== 'Polygon' && activeDataSource !== 'Finnhub' && activeDataSource !== 'YahooFinance' && activeMainSection === 'Identity' && section.key === 'Identity' && (
                  <div className="bg-black/5 border-b border-black">
                    {Object.keys(identitySections)
                      .filter(subSection => {
                        // Only show sub-sections that have data
                        const sectionData = identitySections[subSection]
                        return sectionData && typeof sectionData === 'object' && Object.keys(sectionData).length > 0
                      })
                      .map((subSection) => (
                      <button
                        key={subSection}
                        className={`w-full text-left px-10 py-2.5 text-xs font-medium transition-colors border-b border-black/20 last:border-b-0 ${
                          activeSubSection === subSection
                            ? 'bg-black/10 text-black font-semibold border-l-2 border-l-black'
                            : 'bg-transparent text-black/70 hover:bg-black/5'
                        }`}
                        onClick={() => setActiveSubSection(subSection)}
                      >
                        {subSection}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))
            )}
          </nav>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-auto">
          <div className="p-8">
            {/* Profile Tab Content */}
            {activeDataSource === 'Profile' ? (
              <>
                {profileSections.length === 0 ? (
                  <div className="mb-6 border border-black bg-black/5 p-8 text-center">
                    <p className="text-lg font-medium text-black mb-2">No sections added yet</p>
                    <p className="text-sm text-black/70 mb-4">
                      Click "Add Section" in the sidebar to add sections from any data source.
                    </p>
                    <button
                      className="px-6 py-2 bg-black text-white text-sm font-medium hover:bg-black/90 transition-colors"
                      onClick={() => setShowAddSectionModal(true)}
                    >
                      Add Your First Section
                    </button>
                  </div>
                ) : !activeMainSection || !profileSections.find(s => `${s.source}-${s.sectionKey}` === activeMainSection) ? (
                  <div className="mb-6 border border-black bg-black/5 p-4">
                    <p className="text-sm text-black">
                      Select a section from the sidebar to view its data.
                    </p>
                  </div>
                ) : (
                  <SectionCard 
                    title={getSectionTitle()} 
                    data={getSectionData()} 
                  />
                )}
              </>
            ) : (
              <>
                {/* Data Source Indicator */}
                {!currentSourceData || Object.keys(currentSourceData).length === 0 ? (
                  <div className="mb-6 border border-black bg-black/5 p-6">
                    <div className="text-center">
                      <p className="text-base font-medium text-black mb-2">
                        No data available from {activeDataSource === 'Gemini' ? 'Gemini AI' : activeDataSource === 'YahooFinance' ? 'Yahoo Finance' : activeDataSource === 'Polygon' ? 'Polygon.io' : 'Finnhub'}
                      </p>
                      <p className="text-sm text-black/70 mb-4">
                        Click the <strong>"Fetch"</strong> button above to load data from this source.
                      </p>
                      {activeDataSource === 'Gemini' && (
                        <p className="text-xs text-black/50">
                          Note: Gemini AI fetch takes 30-60 seconds and will open a browser window.
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="mb-4 text-xs text-black/70">
                        Viewing data from: <span className="font-medium">
                          {activeDataSource === 'Gemini' ? 'Gemini AI' : activeDataSource === 'YahooFinance' ? 'Yahoo Finance' : activeDataSource === 'Polygon' ? 'Polygon.io' : 'Finnhub'}
                        </span>
                  </div>
                )}

            {/* Fundamentals Section with Fetch Button */}
            {activeMainSection === 'Fundamentals' && (
              <div className="mb-6 border border-black bg-black/5 p-4">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-black mb-1">Fundamentals Data</h3>
                    <p className="text-sm text-black/70">
                      Fetch comprehensive fundamentals data from Gemini AI
                    </p>
                  </div>
                  <button
                    className="px-6 py-2 bg-black text-white text-sm font-medium hover:bg-black/90 transition-colors disabled:bg-black/50 disabled:cursor-not-allowed"
                    onClick={handleFetchFundamentals}
                    disabled={fundamentalsLoading || !ticker}
                  >
                    {fundamentalsLoading ? 'Fetching...' : 'Fetch from Gemini'}
                  </button>
                </div>
                
                {fundamentalsStatus && (
                  <div className={`p-3 border ${
                    fundamentalsStatus.includes('Failed') 
                      ? 'border-black bg-black/5' 
                      : 'border-black bg-black/5'
                  }`}>
                    <p className="text-sm text-black">{fundamentalsStatus}</p>
                  </div>
                )}
                
                {fundamentalsError && (
                  <div className="p-3 border border-black bg-black/5 mt-2">
                    <p className="text-sm text-black">{fundamentalsError}</p>
                  </div>
                )}
                
                {fundamentalsLoading && (
                  <div className="p-4 border border-black bg-black/5 mt-2">
                    <p className="text-sm text-black mb-2">{fundamentalsStatus || 'Fetching from Gemini AI...'}</p>
                    <p className="text-xs text-black/70">This may take 30-60 seconds. Browser window will open.</p>
                  </div>
                )}
              </div>
            )}
            
                <SectionCard 
                  title={getSectionTitle()} 
                  data={getSectionData()} 
                />
              </>
            )}
          </div>
        </div>
      </div>

      {/* Add Section Modal */}
      {showAddSectionModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowAddSectionModal(false)}>
          <div className="bg-white border-2 border-black max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="border-b-2 border-black px-6 py-4 flex items-center justify-between">
              <h3 className="text-xl font-bold text-black">Add Section</h3>
              <button
                className="text-2xl text-black hover:text-black/70 transition-colors"
                onClick={() => setShowAddSectionModal(false)}
              >
                ×
              </button>
            </div>
            <div className="overflow-y-auto flex-1 p-6">
              {getAllAvailableSections().length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-black/70 mb-4">No sections available from any data source.</p>
                  <p className="text-sm text-black/50">Please fetch data from at least one source first.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {getAllAvailableSections().map((section, index) => {
                    const isAdded = profileSections.some(s => 
                      s.source === section.source && s.sectionKey === section.sectionKey
                    )
                    return (
                      <div
                        key={index}
                        className={`border border-black p-4 flex items-center justify-between ${
                          isAdded ? 'bg-black/5 opacity-60' : 'bg-white hover:bg-black/5'
                        }`}
                      >
                        <div className="flex-1">
                          <p className="font-medium text-black">{section.label}</p>
                          <p className="text-xs text-black/50 mt-1">
                            Source: {section.source === 'YahooFinance' ? 'Yahoo Finance' : section.source}
                          </p>
                        </div>
                        <button
                          className={`px-4 py-2 text-sm font-medium transition-colors ${
                            isAdded
                              ? 'bg-black/20 text-black/50 cursor-not-allowed'
                              : 'bg-black text-white hover:bg-black/90'
                          }`}
                          onClick={() => !isAdded && handleAddSection(section)}
                          disabled={isAdded}
                        >
                          {isAdded ? 'Added' : 'Add'}
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default CompanyProfile
