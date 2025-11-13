/**
 * Direct Yahoo Finance Service (Frontend)
 * Uses CORS proxy to fetch data from Yahoo Finance API
 * Falls back to backend API if direct fetch fails
 */

import { fetchProfileFromYFinance } from './api'

/**
 * Fetch company profile from Yahoo Finance using CORS proxy with backend fallback
 */
export const fetchYahooFinanceDirect = async (ticker) => {
  try {
    console.log(`🔍 [YFINANCE] Attempting direct fetch for: ${ticker}`)
    
    // Yahoo Finance API endpoint
    const modules = [
      'summaryProfile',
      'summaryDetail',
      'assetProfile',
      'defaultKeyStatistics',
      'financialData',
      'quoteType'
    ].join(',')
    
    // Try CORS proxy first
    const yahooUrl = `https://query1.finance.yahoo.com/v10/finance/quoteSummary/${ticker}?modules=${modules}&formatted=true&corsDomain=finance.yahoo.com`
    const proxyUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(yahooUrl)}`
    
    console.log(`🔍 [YFINANCE] Fetching from proxy: ${proxyUrl}`)
    
    const response = await fetch(proxyUrl, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    })
    
    if (!response.ok) {
      throw new Error(`Proxy error: ${response.status}`)
    }
    
    const proxyData = await response.json()
    
    console.log(`🔍 [YFINANCE] Proxy response structure:`, Object.keys(proxyData))
    console.log(`🔍 [YFINANCE] Proxy response.contents type:`, typeof proxyData.contents)
    
    // allorigins returns data in { contents: "..." } format
    let data
    if (proxyData.contents) {
      try {
        // contents might be a string that needs parsing
        if (typeof proxyData.contents === 'string') {
          data = JSON.parse(proxyData.contents)
        } else {
          data = proxyData.contents
        }
        console.log(`🔍 [YFINANCE] Parsed data structure:`, data ? Object.keys(data) : 'null')
      } catch (parseError) {
        console.error(`❌ [YFINANCE] Parse error:`, parseError)
        console.error(`❌ [YFINANCE] Contents value:`, proxyData.contents?.substring(0, 500))
        throw new Error(`Failed to parse proxy response: ${parseError.message}`)
      }
    } else {
      data = proxyData
      console.log(`🔍 [YFINANCE] Using proxyData directly`)
    }
    
    console.log(`🔍 [YFINANCE] Final data structure:`, {
      hasData: !!data,
      hasQuoteSummary: !!(data?.quoteSummary),
      hasResult: !!(data?.quoteSummary?.result),
      resultLength: data?.quoteSummary?.result?.length || 0
    })
    
    if (!data) {
      throw new Error(`No data returned from proxy for ticker: ${ticker}`)
    }
    
    if (!data.quoteSummary) {
      console.error(`❌ [YFINANCE] Missing quoteSummary in data:`, data)
      throw new Error(`Invalid response structure: missing quoteSummary`)
    }
    
    if (!data.quoteSummary.result || data.quoteSummary.result.length === 0) {
      console.error(`❌ [YFINANCE] No results in quoteSummary:`, data.quoteSummary)
      throw new Error(`No data found for ticker: ${ticker}`)
    }
    
    const quoteSummary = data.quoteSummary.result[0]
    
    console.log(`✅ [YFINANCE] Direct fetch successful for: ${ticker}`)
    console.log(`🔍 [YFINANCE] Quote summary structure:`, Object.keys(quoteSummary || {}))
    
    // Extract all modules from quoteSummary and structure them properly
    const companyProfileData = {}
    
    // Map all modules to a flat structure (similar to backend)
    if (quoteSummary) {
      // Add all modules as separate keys
      Object.keys(quoteSummary).forEach(key => {
        if (quoteSummary[key] && typeof quoteSummary[key] === 'object') {
          companyProfileData[key] = quoteSummary[key]
        }
      })
      
      // Also add the full quoteSummary as 'Company Profile' for compatibility
      companyProfileData['Company Profile'] = quoteSummary
    }
    
    console.log(`🔍 [YFINANCE] Company Profile keys:`, Object.keys(companyProfileData))
    
    // Return data directly without wrapping in "What" and "Sources"
    // This allows the frontend to create dynamic buttons from the actual API response keys
    // Remove the duplicate "Company Profile" key if it exists (keep individual modules)
    if (companyProfileData['Company Profile']) {
      // Keep individual modules, remove the duplicate wrapper
      delete companyProfileData['Company Profile']
    }
    
    console.log(`🔍 [YFINANCE] Final data structure keys:`, Object.keys(companyProfileData))
    
    return {
      ticker: ticker.toUpperCase(),
      data: companyProfileData,  // Return directly without wrapper
      success: true
    }
  } catch (error) {
    console.error(`❌ [YFINANCE] Direct fetch failed for ${ticker}:`, error)
    console.log(`🔄 [YFINANCE] Falling back to backend API...`)
    
    // Fallback to backend API
    try {
      console.log(`🔄 [YFINANCE] Attempting backend fallback for: ${ticker}`)
      const backendResult = await fetchProfileFromYFinance(ticker, false) // Don't save to DB from frontend
      
      console.log(`🔍 [YFINANCE] Backend result:`, backendResult)
      console.log(`🔍 [YFINANCE] Backend result.data:`, backendResult?.data)
      console.log(`🔍 [YFINANCE] Backend result.data.What:`, backendResult?.data?.What)
      
      if (backendResult && backendResult.data) {
        // Check if data is actually populated (not just null)
        const hasData = backendResult.data.What && 
                       Object.keys(backendResult.data.What).length > 0 &&
                       !Object.values(backendResult.data.What).every(val => val === null)
        
        if (hasData) {
          console.log(`✅ [YFINANCE] Backend fallback successful with data for: ${ticker}`)
          return backendResult
        } else {
          console.warn(`⚠️ [YFINANCE] Backend returned structure but data is null/empty`)
          throw new Error('Backend API returned empty data (likely rate limited)')
        }
      } else {
        throw new Error('Backend API returned no data structure')
      }
    } catch (backendError) {
      console.error(`❌ [YFINANCE] Backend fallback also failed:`, backendError)
      
      // Provide helpful error message
      let errorMessage = `Failed to fetch data from Yahoo Finance for ${ticker}`
      
      if (error.message.includes('CORS') || error.message.includes('NetworkError') || error.message.includes('Failed to fetch')) {
        errorMessage = 'CORS error: Both direct fetch and backend API failed. Please check your connection and try again.'
      } else if (error.message.includes('429') || backendError.message?.includes('429') || backendError.message?.includes('rate limit')) {
        errorMessage = 'Rate limit exceeded. Please wait 5-10 minutes and try again. Yahoo Finance has strict rate limits.'
      } else if (backendError.message?.includes('empty data')) {
        errorMessage = 'Yahoo Finance rate limit active. Please wait a few minutes before trying again.'
      }
      
      throw new Error(errorMessage)
    }
  }
}

/**
 * Fetch additional data (optional - for future use)
 */
export const fetchYahooFinanceQuote = async (ticker) => {
  try {
    const quote = await yahooFinance.quote(ticker)
    return quote
  } catch (error) {
    console.error(`❌ [YFINANCE] Error fetching quote for ${ticker}:`, error)
    throw error
  }
}

/**
 * Fetch historical data (optional - for future use)
 */
export const fetchYahooFinanceHistory = async (ticker, period = '1mo') => {
  try {
    const history = await yahooFinance.historical(ticker, {
      period1: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
      period2: new Date()
    })
    return history
  } catch (error) {
    console.error(`❌ [YFINANCE] Error fetching history for ${ticker}:`, error)
    throw error
  }
}

