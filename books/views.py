# books/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics, permissions
from .models import Book, BookBorrow
from .serializers import BookSerializer, BookBorrowSerializer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.http import FileResponse
from django.http import HttpResponse
from .models import Tag
from .serializers import TagSerializer
from rest_framework.parsers import MultiPartParser, FormParser

def home(request):
    return HttpResponse("Welcome to Books API!")

class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]

class BookListView(generics.ListAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticated]

class BookDetailView(generics.RetrieveAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticated]

class BorrowBookView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if hasattr(user, 'profile') and user.profile.user_type != 'reader':
            return Response({"error": "Only readers can borrow books."},
                            status=status.HTTP_403_FORBIDDEN)
        book_id = request.data.get('book_id')
        book = get_object_or_404(Book, id=book_id)
        if not book.is_available:
            return Response({"error": "Book is not available."},
                            status=status.HTTP_400_BAD_REQUEST)
        borrow = BookBorrow.objects.create(reader=request.user, book=book)
        book.borrow_count += 1
        book.save()
        return Response({'message': 'Book borrowed successfully!', 'borrow_id': borrow.id},
                        status=status.HTTP_201_CREATED)

class ReturnBookView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, borrow_id):
        try:
            # Find the borrow record and verify ownership
            borrow = BookBorrow.objects.select_related('book').get(
                id=borrow_id,
                user=request.user,
                is_returned=False
            )
            
            # Mark as returned
            borrow.is_returned = True
            borrow.return_date = timezone.now()
            borrow.save()

            # Log the return
            print(f"Book returned: Borrow ID {borrow_id} by user {request.user.id}")

            return Response({
                "status": "success",
                "message": "Book returned successfully"
            })

        except BookBorrow.DoesNotExist:
            return Response({
                "status": "error",
                "message": "Borrow record not found or already returned"
            }, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            print(f"Error returning book: {str(e)}")
            return Response({
                "status": "error",
                "message": "Failed to return book"
            }, status=status.HTTP_400_BAD_REQUEST)

class AddBookView(generics.CreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        serializer.save(publisher=self.request.user)

class RemoveBookView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, book_id):
        user = request.user
        book = get_object_or_404(Book, id=book_id, publisher=user)
        book.delete()
        return Response({"message": "Book removed successfully."},
                        status=status.HTTP_200_OK)

class ReaderAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if hasattr(user, 'profile') and user.profile.user_type != 'reader':
            return Response({"error": "Not authorized."},
                            status=status.HTTP_403_FORBIDDEN)
        borrowed = BookBorrow.objects.filter(reader=user)
        borrow_serializer = BookBorrowSerializer(borrowed, many=True)
        data = {
            "user": {
                "name": user.username,
                "email": user.email,
                "role": user.profile.user_type,
                "registered_at": user.date_joined,
                "borrow_count": borrowed.count(),
                "profile_image": "",  # เพิ่ม field รูปโปรไฟล์หากมี
            },
            "borrowed_books": borrow_serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)

class PublisherAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.profile.user_type != 'publisher':
            return Response({"error": "Not authorized."},
                            status=status.HTTP_403_FORBIDDEN)
        published_books = Book.objects.filter(publisher=user)
        serializer = BookSerializer(published_books, many=True)
        data = {
            "user": {
                "name": user.first_name,
                "email": user.email,
                "role": user.profile.user_type,
                "registered_at": user.date_joined,
                "book_count": published_books.count(),
                "profile_image": "",  # เพิ่ม field รูปโปรไฟล์หากมี
            },
            "published_books": serializer.data
        }
        return Response(data, status=status.HTTP_200_OK)

class ReadBookView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, borrow_id):
        borrow_entry = get_object_or_404(BookBorrow, id=borrow_id, reader=request.user)
        now = timezone.now()
        if now > borrow_entry.due_date:
            borrow_entry.delete()
            return Response({"error": "Borrow period expired. This book is no longer accessible."},
                            status=status.HTTP_403_FORBIDDEN)
        book = borrow_entry.book
        if not book.pdf_file:
            return Response({"error": "PDF not available."},
                            status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(book.pdf_file.open('rb'), content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="{}"'.format(book.pdf_file.name)
        return response

class EditBookView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, book_id):
        try:
            # Get book and verify ownership
            book = Book.objects.get(id=book_id, publisher=request.user)
            
            # Update book with partial data
            serializer = BookSerializer(
                book,
                data=request.data,
                partial=True  # Allow partial updates
            )
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Book.DoesNotExist:
            return Response(
                {"detail": "Book not found or you don't have permission to edit it"},
                status=status.HTTP_404_NOT_FOUND
            )