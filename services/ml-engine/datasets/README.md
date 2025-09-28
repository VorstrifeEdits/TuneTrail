# TuneTrail ML Engine - Data Sources

## Overview
This directory contains scripts to ingest music datasets for training recommendation models. You don't need millions of tracks to start - 10,000-50,000 tracks are sufficient for training and validation.

## Available Free Datasets

### 1. Free Music Archive (FMA)
**Best for: Development & Beta Testing**

- **Size**: 106,574 tracks (Creative Commons)
- **Metadata**: Genre, artist, album, year
- **Audio**: 30-second clips available
- **License**: Creative Commons (various)

**Download**: https://github.com/mdeff/fma

```bash
# Small subset (8,000 tracks, 7.2 GB)
wget https://os.unil.cloud.switch.ch/fma/fma_small.zip

# Medium subset (25,000 tracks, 22 GB)
wget https://os.unil.cloud.switch.ch/fma/fma_medium.zip
```

### 2. Million Song Dataset
**Best for: Feature Training**

- **Size**: 1M tracks (metadata only)
- **Audio Features**: Pre-computed (tempo, key, loudness, etc.)
- **Metadata**: Artist, album, year, tags
- **Audio**: Not included (use Spotify API for previews)

**Download**: http://millionsongdataset.com/

```bash
# Subset (10,000 tracks)
wget http://static.echonest.com/millionsongsubset.tar.gz
```

### 3. Spotify Web API
**Best for: Preview Tracks & Metadata**

- **30-second previews**: Legal for development
- **Audio features**: Built-in API endpoints
- **Rate limits**: 100 requests/minute (free tier)

**Setup**:
1. Create app at https://developer.spotify.com/dashboard
2. Get Client ID & Secret
3. Use our ingestion script in `ingestion/spotify_api.py`

### 4. MusicBrainz
**Best for: Metadata Enrichment**

- **Database**: 2M+ artists, 4M+ releases
- **Metadata**: Comprehensive music encyclopedia
- **License**: CC0 (public domain)
- **API**: Free, no rate limits

**Access**: https://musicbrainz.org/doc/MusicBrainz_API

### 5. Last.fm Dataset
**Best for: Collaborative Filtering Training**

- **360K users** listening histories
- **160M listening events**
- **Implicit feedback** (play counts)

**Download**: http://www.dtic.upf.edu/~ocelma/MusicRecommendationDataset/lastfm-360K.html

## Recommended Approach

### Phase 1: Development (Now)
1. Download **FMA Small** (8K tracks, 7.2 GB)
2. Extract audio features with audio-processor service
3. Train Free + Starter tier models
4. Validate with test users

### Phase 2: Beta Launch (Month 2)
1. Add **FMA Medium** (25K tracks)
2. Augment with **Spotify preview tracks**
3. Train Pro tier models (NCF)
4. Enable user uploads

### Phase 3: Production (Month 3+)
1. User-contributed music (self-hosted)
2. SaaS users link streaming accounts
3. Partner with indie labels
4. License Creative Commons catalogs

## Storage Requirements

| Dataset | Tracks | Size | Use Case |
|---------|--------|------|----------|
| FMA Small | 8K | 7.2 GB | Development |
| FMA Medium | 25K | 22 GB | Beta testing |
| Spotify Previews | Variable | API only | Augmentation |
| User Uploads | Growing | Variable | Production |

## Legal Considerations

✅ **Safe to Use:**
- FMA (Creative Commons)
- Million Song Dataset (metadata)
- Spotify preview URLs (30-sec clips)
- MusicBrainz (CC0)
- Last.fm dataset (research)

❌ **Do NOT:**
- Scrape full Spotify tracks
- Redistribute copyrighted music
- Use datasets for commercial training without license

## Next Steps

1. Run ingestion scripts in `ingestion/` directory
2. Process audio with `audio-processor` service
3. Train models with `scripts/train_all_models.py`
4. Monitor progress in TensorBoard

## Questions?

The "chicken-and-egg" problem is solved! Start with 8K tracks from FMA Small, demonstrate value, attract users, grow library organically.