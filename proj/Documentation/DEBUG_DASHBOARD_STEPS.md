# Debug Dashboard - Quick Steps

**Issue:** Dashboard shows counts but not actual items

---

## Step 1: Clear Browser Cache

**IMPORTANT:** Your browser might be caching the old version!

### How to Hard Refresh:
- **Chrome/Edge:** `Ctrl + Shift + R` (Windows) or `Cmd + Shift + R` (Mac)
- **Firefox:** `Ctrl + F5` (Windows) or `Cmd + Shift + R` (Mac)

---

## Step 2: Open Browser Console

1. Press `F12` on your keyboard
2. Click the "Console" tab
3. Refresh the dashboard page

---

## Step 3: Check Console Output

You should see logs like this:

```
📊 Fetching performance data for project: <project-id>
📊 Received data: {success: true, milestones: {...}, ...}
✅ Success! Updating dashboard...
   Milestones: {count: 6, details_count: 0}
   Tasks: {count: 7, details_count: 0}
   Bottlenecks: {count: 3, details_count: 0}
   Completion: 0
📋 Fetching detailed items...
📋 Summary received: {milestones: Array(6), tasks: Array(7), ...}
   Milestones array: [6 items]
   Tasks array: [7 items]
   Bottlenecks array: [3 items]
```

---

## Step 4: What the Logs Mean

### ✅ **GOOD** - If you see:
```
📊 Fetching performance data...
✅ Success! Updating dashboard...
📋 Milestones array: Array(6)
```
→ Data is loading, UI should update

### ❌ **BAD** - If you see:
```
No project ID available
```
→ Project ID not detected

### ❌ **BAD** - If you see:
```
Failed to load performance data: ...
```
→ API error

---

## Step 5: Copy Console Output

**Copy ALL the console output and send it to me** so I can see what's happening.

---

## Quick Fix Checklist

- [ ] Hard refresh the page (Ctrl + Shift + R)
- [ ] Open console (F12)
- [ ] Check for JavaScript errors (red text)
- [ ] Look for the 📊 and 📋 log messages
- [ ] Copy console output

---

## Common Issues

### Issue: "No project ID available"
**Fix:** Make sure you're on the performance dashboard page:  
`http://localhost:5000/performance_agent/dashboard/<project-id>`

### Issue: API 404 errors
**Fix:** Make sure Flask server is running

### Issue: Data shows but UI doesn't update
**Fix:** Browser cache - do hard refresh!

---

## If Still Not Working

Send me:
1. ✅ Full console output
2. ✅ The URL you're viewing
3. ✅ Any errors (red text in console)

I'll diagnose the exact issue!

