# Video Processor Frontend

A modern, responsive web application for uploading and processing videos using AI-powered analysis.

## 🚀 Features

- **Drag & Drop Upload**: Intuitive file upload with drag-and-drop support
- **Progress Tracking**: Real-time upload progress with visual progress bars
- **S3 Integration**: Direct upload to S3 using presigned URLs
- **Video Processing**: AI-powered video analysis and segmentation
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Modern UI**: Beautiful gradient design with smooth animations

## 📋 Prerequisites

- Your Modal backend deployed and running
- Vercel account (free tier works perfectly)

## 🔧 Setup Instructions

### 1. Update API URL

The API URLs are already configured in `index.html`:

```javascript
// Lines 267-268 in index.html
const API_BASE_URL = 'https://lu-labs--script-trimmer-get-presigned-url-endpoint.modal.run';
const PROCESSING_API_URL = 'https://lu-labs--script-trimmer-extract-audio-endpoint.modal.run';
```

These URLs are already set to your Modal endpoints.

### 2. Deploy to Vercel

#### Option A: Deploy via Vercel CLI

1. Install Vercel CLI:

```bash
npm i -g vercel
```

2. Login to Vercel:

```bash
vercel login
```

3. Deploy:

```bash
vercel
```

#### Option B: Deploy via GitHub

1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Click "New Project"
4. Import your GitHub repository
5. Deploy

#### Option C: Deploy via Vercel Dashboard

1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Choose "Upload" and upload your files
4. Deploy

## 🎯 Usage Guide

### Step 1: Upload Video

1. **Select File**: Click the upload area or drag & drop a video file
2. **File Validation**: The app validates file type and size (max 2GB)
3. **Upload to S3**: Click "Upload to S3" to start the upload process
4. **Progress Tracking**: Watch the real-time progress bar
5. **Confirmation**: See upload status and video information

### Step 2: Process Video

1. **Process Button**: After successful upload, click "Process Video"
2. **Processing**: The app calls your Modal backend for video analysis
3. **Results**: View processing results including:
   - Audio extraction details
   - Video segments
   - S3 file URLs
   - Processing time

## 📁 File Structure

```
├── index.html          # Main application file
├── vercel.json         # Vercel deployment configuration
└── README_FRONTEND.md  # This file
```

## 🔧 Configuration

### API Endpoints

The frontend expects these Modal endpoints:

1. **GET Presigned URL**: `POST https://lu-labs--script-trimmer-get-presigned-url-endpoint.modal.run`

   ```json
   {
     "filename": "video.mp4",
     "content_type": "video/mp4"
   }
   ```

2. **Process Video**: `POST https://lu-labs--script-trimmer-extract-audio-endpoint.modal.run`
   ```json
   {
     "s3_url": "https://your-bucket.s3.amazonaws.com/video.mp4"
   }
   ```

### File Size Limits

- **Maximum file size**: 2GB
- **Supported formats**: MP4, AVI, MOV, MKV, and other video formats

## 🎨 Customization

### Colors

The app uses a purple gradient theme. To change colors, modify these CSS variables in `index.html`:

```css
/* Main gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Button gradient */
background: linear-gradient(135deg, #667eea, #764ba2);
```

### Styling

All styles are included in the `<style>` tag within `index.html` for easy modification.

## 🔒 Security Features

- **CORS Headers**: Configured in `vercel.json`
- **Content Security**: XSS protection headers
- **File Validation**: Client-side file type and size validation

## 🐛 Troubleshooting

### Common Issues

1. **CORS Errors**

   - Ensure your Modal app allows requests from your Vercel domain
   - Add your Vercel URL to Modal's CORS settings

2. **Upload Fails**

   - Check if the presigned URL is valid
   - Verify S3 bucket permissions
   - Check browser console for errors

3. **Processing Fails**
   - Verify Modal app is running
   - Check Modal logs for errors
   - Ensure all environment variables are set

### Debug Mode

Open browser console (F12) to see detailed logs and error messages.

## 📱 Mobile Support

The app is fully responsive and works on:

- ✅ Desktop browsers
- ✅ Tablets
- ✅ Mobile phones
- ✅ Touch devices

## 🚀 Performance

- **Fast Loading**: Optimized CSS and minimal dependencies
- **Efficient Uploads**: Direct S3 uploads bypass server bandwidth
- **Progressive Enhancement**: Works even with JavaScript disabled (basic functionality)

## 📞 Support

If you encounter issues:

1. Check browser console for errors
2. Verify Modal app logs
3. Test API endpoints directly
4. Check Vercel deployment logs

## 🔄 Updates

To update the frontend:

1. Modify `index.html`
2. Redeploy to Vercel: `vercel --prod`
3. Or push to GitHub for automatic deployment

---

**Happy Video Processing! 🎬✨**
