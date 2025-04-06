from django.shortcuts import render,redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from pytubefix import YouTube
from django.conf import settings
import os
import assemblyai as aai
import openai
from urllib.parse import urlparse, parse_qs
import time
from .models import BlogPost
# Create your views here.
@login_required
def index(request):
    return render(request,'index.html')

@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data.get('link')
            
            if not yt_link:
                return JsonResponse({'error': 'No YouTube link provided'}, status=400)

            # Get video title first to validate the link
            title = yt_title(yt_link)
            if not title:
                return JsonResponse({
                    'error': 'Could not process YouTube video. Please ensure the video is:\n' +
                            '- Publicly accessible\n' +
                            '- Not age-restricted\n' +
                            '- A valid YouTube URL'
                }, status=400)
            
            # Continue with transcription if title was successful
            transcription = get_transcription(yt_link)
            if not transcription:
                return JsonResponse({'error': 'Failed to get transcript'}, status=500)
            
            blog_content = generate_blog_from_transcription(transcription)
            if not blog_content:
                return JsonResponse({'error': 'Failed to generate blog'}, status=500)

            new_blog_article = BlogPost.objects.create(
                user=request.user,
                youtube_title=title,
                youtube_link=yt_link,
                generated_content=blog_content,
            )
            new_blog_article.save()
            return JsonResponse({'content': blog_content})
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def generate_blog_from_transcription(transcription):
    openai.api_key = #"Add you key here"
    prompt = f"Based on the following transcript from a youtube vide, write a comprehensive blog article, donot make it look like a youtube video, make it look like a proper blog article:\n\n{transcription}\n\nArticle:"

    response = openai.completions.create(
        model= "gpt-3.5-turbo-instruct",
        prompt=prompt,
        max_tokens=1000
    )

    generated_content = response.choices[0].text.strip()

    return generated_content

def yt_title(link):
    try:
        # Initialize YouTube
        yt = YouTube(link)
        
        # Add a small delay before accessing properties
        time.sleep(2)
        
        if not yt.title:
            print("Could not get video title")
            return None
            
        return yt.title
        
    except Exception as e:
        print(f"YouTube processing error: {str(e)}")
        return None

def download_audio(link):
    try:
        yt = YouTube(link)
        # Get audio stream
        video = yt.streams.filter(only_audio=True).first()
        if not video:
            print("No audio stream available")
            return None
            
        out_file = video.download(output_path=settings.MEDIA_ROOT)
        base, ext = os.path.splitext(out_file)
        new_file = base + '.mp3'
        os.rename(out_file, new_file)
        return new_file
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        return None

def get_transcription(link):
    audio_file = download_audio(link)
    aai.settings.api_key = #"Add your API key"

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(audio_file)

    return transcript.text

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        # Fix: Changed parameter name from 'user' to 'username'
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            error_message = 'Invalid username or Password'
            return render(request, 'login.html', {'error_message': error_message})

    return render(request, 'login.html')

def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user) 
    return render(request,"all-blogs.html",{'blog-articles': blog_articles})

def blog_details(request,pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user == blog_article_detail.user:
        return render(request,'blog-details.html', {'blog_article_detail':blog_article_detail})
    else:
        return redirect('/')

def user_signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        repeatpassword = request.POST['repeatpassword']

        if password == repeatpassword:
            try:
                user = User.objects.create_user(username,email,password)
                user.save()
                login(request,user)
                return redirect('/')
            except:
                error_message = 'Error creating account!'
                return render(request,'signup.html',{'error_message':error_message})

        else:
            error_message = 'Passwords donot match!'
            return render(request,'signup.html',{'error_message':error_message})

            
    return render(request,'signup.html')

def user_logout(request):
    logout(request)
    return redirect('/')