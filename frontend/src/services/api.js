/**
 * API Service for Backend Communication
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

/**
 * Upload a JSON file to the backend
 */
export const uploadProfile = async (file) => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/profiles/upload`, {
    method: 'POST',
    body: formData
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to upload profile')
  }

  return await response.json()
}

/**
 * Get all company profiles
 */
export const getAllProfiles = async (skip = 0, limit = 100) => {
  const response = await fetch(`${API_BASE_URL}/profiles/?skip=${skip}&limit=${limit}`)

  if (!response.ok) {
    throw new Error('Failed to fetch profiles')
  }

  return await response.json()
}

/**
 * Get profile by ID
 */
export const getProfileById = async (id) => {
  const response = await fetch(`${API_BASE_URL}/profiles/${id}`)

  if (!response.ok) {
    throw new Error('Profile not found')
  }

  return await response.json()
}

/**
 * Get profile by ticker
 */
export const getProfileByTicker = async (ticker) => {
  const response = await fetch(`${API_BASE_URL}/profiles/ticker/${ticker}`)

  if (!response.ok) {
    throw new Error('Profile not found')
  }

  return await response.json()
}

/**
 * Search profiles by query
 */
export const searchProfiles = async (query) => {
  const response = await fetch(`${API_BASE_URL}/profiles/search/${encodeURIComponent(query)}`)

  if (!response.ok) {
    throw new Error('Search failed')
  }

  return await response.json()
}

/**
 * Delete profile
 */
export const deleteProfile = async (id) => {
  const response = await fetch(`${API_BASE_URL}/profiles/${id}`, {
    method: 'DELETE'
  })

  if (!response.ok) {
    throw new Error('Failed to delete profile')
  }

  return await response.json()
}

/**
 * Create profile manually
 */
export const createProfile = async (ticker, data) => {
  const response = await fetch(`${API_BASE_URL}/profiles/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      ticker,
      data
    })
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create profile')
  }

  return await response.json()
}

/**
 * Fetch company profile from Gemini AI
 */
export const fetchProfileFromGemini = async (ticker, saveToDb = true) => {
  const response = await fetch(`${API_BASE_URL}/gemini/fetch-profile`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      ticker: ticker.toUpperCase(),
      save_to_db: saveToDb
    })
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch profile from Gemini')
  }

  return await response.json()
}

/**
 * Fetch company profile from Gemini AI (GET method)
 */
export const fetchProfileFromGeminiGet = async (ticker, saveToDb = true) => {
  const response = await fetch(
    `${API_BASE_URL}/gemini/fetch-profile/${ticker.toUpperCase()}?save_to_db=${saveToDb}`
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch profile from Gemini')
  }

  return await response.json()
}

/**
 * Fetch fundamentals from Gemini AI
 */
export const fetchFundamentalsFromGemini = async (ticker, saveToDb = true) => {
  const response = await fetch(`${API_BASE_URL}/fundamentals/fetch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      ticker: ticker.toUpperCase(),
      save_to_db: saveToDb
    })
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch fundamentals from Gemini')
  }

  return await response.json()
}

/**
 * Fetch fundamentals from Gemini AI (GET method)
 */
export const fetchFundamentalsFromGeminiGet = async (ticker, saveToDb = true) => {
  const response = await fetch(
    `${API_BASE_URL}/fundamentals/fetch/${ticker.toUpperCase()}?save_to_db=${saveToDb}`
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch fundamentals from Gemini')
  }

  return await response.json()
}

/**
 * Fetch company profile from Yahoo Finance
 */
export const fetchProfileFromYFinance = async (ticker, saveToDb = true) => {
  const response = await fetch(`${API_BASE_URL}/yfinance/fetch-data`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      ticker: ticker.toUpperCase(),
      save_to_db: saveToDb
    })
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch profile from Yahoo Finance')
  }

  return await response.json()
}

/**
 * Fetch company profile from Yahoo Finance (GET method)
 */
export const fetchProfileFromYFinanceGet = async (ticker, saveToDb = true) => {
  const response = await fetch(
    `${API_BASE_URL}/yfinance/fetch-data/${ticker.toUpperCase()}?save_to_db=${saveToDb}`
  )

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch profile from Yahoo Finance')
  }

  return await response.json()
}

/**
 * Fetch company profile from Polygon.io
 */
export const fetchProfileFromPolygon = async (ticker, saveToDb = true) => {
  const response = await fetch(`${API_BASE_URL}/polygon/fetch-profile`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      ticker: ticker.toUpperCase(),
      save_to_db: saveToDb
    })
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch profile from Polygon.io')
  }

  return await response.json()
}

  /**
   * Fetch company profile from Polygon.io (GET method)
   */
  export const fetchProfileFromPolygonGet = async (ticker, saveToDb = true) => {
    const response = await fetch(
      `${API_BASE_URL}/polygon/fetch-profile/${ticker.toUpperCase()}?save_to_db=${saveToDb}`
    )

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch profile from Polygon.io')
    }

    return await response.json()
  }

  /**
   * Fetch data from Finnhub
   */
  export const fetchDataFromFinnhub = async (ticker, saveToDb = true) => {
    const response = await fetch(`${API_BASE_URL}/finnhub/fetch-data`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        ticker: ticker.toUpperCase(),
        save_to_db: saveToDb
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch data from Finnhub')
    }

    return await response.json()
  }

  /**
   * Fetch data from Finnhub (GET method)
   */
  export const fetchDataFromFinnhubGet = async (ticker, saveToDb = true) => {
    const response = await fetch(
      `${API_BASE_URL}/finnhub/fetch-data/${ticker.toUpperCase()}?save_to_db=${saveToDb}`
    )

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to fetch data from Finnhub')
    }

    return await response.json()
  }

