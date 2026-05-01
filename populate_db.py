import os
import django

# Django ayarlarını yükle
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from identity.models import User, Role
from departments.models import Department, Category
from tickets.models import Ticket, Status, Priority, TicketHistory
from notifications.models import Notification

def populate():
    print("Mevcut veriler güncelleniyor / Yeni veriler oluşturuluyor...\n")

    # 1. Departmanlar (En az 3 adet)
    dept_it, _ = Department.objects.get_or_create(name='Bilgi İşlem', defaults={'description': 'IT ve teknik destek departmanı'})
    dept_hr, _ = Department.objects.get_or_create(name='İnsan Kaynakları', defaults={'description': 'Personel ve özlük hakları yönetimi'})
    dept_acc, _ = Department.objects.get_or_create(name='Muhasebe', defaults={'description': 'Mali işler ve faturalandırma'})
    depts = [dept_it, dept_hr, dept_acc]
    print(f"✅ 3 Adet Departman eklendi/doğrulandı.")

    # 2. Kategoriler (Her biri IT'ye ait örnek kategoriler - En az 3 adet)
    cat_net, _ = Category.objects.get_or_create(department=dept_it, name='Ağ Sorunları', defaults={'description': 'İnternet arızaları'})
    cat_sw, _ = Category.objects.get_or_create(department=dept_it, name='Yazılım Desteği', defaults={'description': 'Uygulama hataları'})
    cat_hw, _ = Category.objects.get_or_create(department=dept_it, name='Donanım İhtiyacı', defaults={'description': 'Bilgisayar malzemesi talepleri'})
    cats = [cat_net, cat_sw, cat_hw]
    print(f"✅ 3 Adet Kategori (IT Altında) eklendi/doğrulandı.")

    # 3. Kullanıcılar (En az 3) ve Rolleri
    # Admin
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'admin123', role=Role.ADMIN)
    else:
        admin = User.objects.get(username='admin')

    managers, agents, employees = [], [], []
    roles_list = ['MANAGER', 'AGENT', 'EMPLOYEE']
    
    for role in roles_list:
        for j in range(1, 4):
            username = f"{role.lower()}_{j}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'role': getattr(Role, role),
                    'department': depts[j-1] if role in ['MANAGER', 'AGENT'] else None,
                    'is_active': True
                }
            )
            if created:
                user.set_password('pass123')
                user.save()
            
            # Yöneticileri departmanlarına tanımla
            if role == 'MANAGER':
                managers.append(user)
                depts[j-1].manager = user
                depts[j-1].save()
            elif role == 'AGENT':
                agents.append(user)
            elif role == 'EMPLOYEE':
                employees.append(user)
                
    print(f"✅ 9 Adet Kullanıcı (3 Yön, 3 Personel, 3 Çalışan) ve 1 Admin eklendi. (Şifreler: pass123 / Admin: admin123)")

    # 4. Biletler (En az 3 adet, Farklı Status ve Priority'lerde)
    tickets = []
    statuses = [Status.OPEN, Status.IN_PROGRESS, Status.CLOSED]
    priorities = [Priority.LOW, Priority.NORMAL, Priority.URGENT]
    
    for i in range(3):
        ticket, created = Ticket.objects.get_or_create(
            subject=f'Sistem Hatası Bildirimi {i+1}',
            defaults={
                'message': f'Bu otomatik olarak oluşturulmuş bir test bileti denemesidir. Lütfen en kısa sürede {cats[i].name} ile ilgilenin.',
                'status': statuses[i],
                'priority': priorities[i],
                'sender': employees[i],
                'department': dept_it,
                'category': cats[i]
            }
        )
        
        # Bilet açıksa boşa bırak, işleme alındıysa veya kapalıysa agent ata
        if ticket.status != Status.OPEN:
            ticket.assigned_to = agents[0]
            if ticket.status == Status.CLOSED:
                ticket.resolution_note = 'Müşterinin sorunu giderildi ve cihaz teslim edildi.'
            ticket.save()
            
        tickets.append(ticket)
        
        # 5. Ticket History (Bilet Geçmişi - En az 3 adet)
        TicketHistory.objects.get_or_create(
            ticket=ticket,
            actor=employees[i],
            action='Talep sistemi üzerinden oluşturuldu.'
        )
    print(f"✅ 3 Adet Bilet (Farklı durumlarda) ve 3 Adet Bilet Geçmişi eklendi.")

    # 6. Bildirimler (Notification - En az 3 adet)
    for i in range(3):
        Notification.objects.get_or_create(
            recipient=agents[0],
            message=f'Yeni bildirim: #{tickets[i].id} numaralı {tickets[i].subject} biletiniz mevcut.',
            defaults={
                'ticket': tickets[i]
            }
        )
    print(f"✅ 3 Adet Bildirim 'agent_1' kullanıcısına eklendi/doğrulandı.")

    print("\n🎉 Tebrikler! Veritabanı başarıyla her modelden en az 3 data içerecek şekilde dolduruldu.")

if __name__ == '__main__':
    populate()
