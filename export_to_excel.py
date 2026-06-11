#!/usr/bin/env python3
"""
Скрипт для экспорта данных из базы данных в Excel файлы
Используется после окончания розыгрыша для анализа всей собранной информации
"""

import asyncio
from datetime import datetime
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import get_settings
from app.db.models import User, Campaign, Referral, Ticket, DrawResult, AuditLog
from app.db.session import build_engine


def _strip_tz(value):
    """Убирает timezone из datetime, чтобы Excel мог записать дату."""
    if value is not None and hasattr(value, 'tzinfo') and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value


async def export_data_to_excel(output_dir="exports"):
    """
    Экспортирует все данные из базы данных в Excel файлы
    """
    import os
    # Создаем директорию для экспорта, если она не существует
    os.makedirs(output_dir, exist_ok=True)
    
    settings = get_settings()
    engine = build_engine(settings)
    
    try:
        async with AsyncSession(engine) as session:
            # Экспорт пользователей
            users_result = await session.execute(select(User))
            users_data = users_result.scalars().all()
            
            # Преобразуем в список словарей
            users_list = []
            for user in users_data:
                user_dict = {
                    'id': user.id,
                    'telegram_id': user.telegram_id,
                    'username': user.username,
                    'ref_code': user.ref_code,
                    'referred_by': user.referred_by,
                    'age': user.age,
                    'favorite_sport': user.favorite_sport,
                    'is_blocked': user.is_blocked,
                    'created_at': _strip_tz(user.created_at)
                }
                users_list.append(user_dict)
            
            # Создаем DataFrame для пользователей
            users_df = pd.DataFrame(users_list)
            
            # Экспорт кампаний
            campaigns_result = await session.execute(select(Campaign))
            campaigns_data = campaigns_result.scalars().all()
            
            # Преобразуем в список словарей
            campaigns_list = []
            for campaign in campaigns_data:
                campaign_dict = {
                    'id': campaign.id,
                    'title': campaign.title,
                    'starts_at': _strip_tz(campaign.starts_at),
                    'ends_at': _strip_tz(campaign.ends_at),
                    'status': campaign.status.value if hasattr(campaign.status, 'value') else campaign.status,
                    'top_k': campaign.top_k,
                    'min_days_subscribed': campaign.min_days_subscribed,
                    'created_at': _strip_tz(campaign.created_at)
                }
                campaigns_list.append(campaign_dict)
            
            # Создаем DataFrame для кампаний
            campaigns_df = pd.DataFrame(campaigns_list)
            
            # Экспорт рефералов
            referrals_result = await session.execute(select(Referral))
            referrals_data = referrals_result.scalars().all()
            
            # Преобразуем в список словарей
            referrals_list = []
            for referral in referrals_data:
                referral_dict = {
                    'id': referral.id,
                    'inviter_id': referral.inviter_id,
                    'invitee_id': referral.invitee_id,
                    'campaign_id': referral.campaign_id,
                    'status': referral.status.value if hasattr(referral.status, 'value') else referral.status,
                    'verified_at': _strip_tz(referral.verified_at),
                    'created_at': _strip_tz(referral.created_at)
                }
                referrals_list.append(referral_dict)
            
            # Создаем DataFrame для рефералов
            referrals_df = pd.DataFrame(referrals_list)
            
            # Экспорт билетов
            tickets_result = await session.execute(select(Ticket))
            tickets_data = tickets_result.scalars().all()
            
            # Преобразуем в список словарей
            tickets_list = []
            for ticket in tickets_data:
                ticket_dict = {
                    'id': ticket.id,
                    'user_id': ticket.user_id,
                    'campaign_id': ticket.campaign_id,
                    'amount': ticket.amount,
                    'reason': ticket.reason,
                    'source_referral_id': ticket.source_referral_id,
                    'idempotency_key': ticket.idempotency_key,
                    'created_at': _strip_tz(ticket.created_at)
                }
                tickets_list.append(ticket_dict)
            
            # Создаем DataFrame для билетов
            tickets_df = pd.DataFrame(tickets_list)
            
            # Экспорт результатов розыгрыша
            draw_results_result = await session.execute(select(DrawResult))
            draw_results_data = draw_results_result.scalars().all()
            
            # Преобразуем в список словарей
            draw_results_list = []
            for draw_result in draw_results_data:
                draw_result_dict = {
                    'id': draw_result.id,
                    'campaign_id': draw_result.campaign_id,
                    'winner_user_id': draw_result.winner_user_id,
                    'seed_info': draw_result.seed_info,
                    'drawn_at': _strip_tz(draw_result.drawn_at)
                }
                draw_results_list.append(draw_result_dict)
            
            # Создаем DataFrame для результатов розыгрыша
            draw_results_df = pd.DataFrame(draw_results_list)
            
            # Экспорт логов аудита
            audit_logs_result = await session.execute(select(AuditLog))
            audit_logs_data = audit_logs_result.scalars().all()
            
            # Преобразуем в список словарей
            audit_logs_list = []
            for log in audit_logs_data:
                log_dict = {
                    'id': log.id,
                    'action': log.action,
                    'actor_user_id': log.actor_user_id,
                    'target_id': log.target_id,
                    'details': log.details,
                    'created_at': _strip_tz(log.created_at)
                }
                audit_logs_list.append(log_dict)
            
            # Создаем DataFrame для логов аудита
            audit_logs_df = pd.DataFrame(audit_logs_list)
        
        # Генерируем имя файла с временной меткой
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{output_dir}/telegram_bot_export_{timestamp}.xlsx"
        
        # Создаем Excel файл с несколькими листами
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            users_df.to_excel(writer, sheet_name='Users', index=False)
            
            # Добавляем форматирование для листа Users
            workbook = writer.book
            worksheet_users = writer.sheets['Users']
            
            # Автоподбор ширины столбцов для Users
            for column in worksheet_users.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Ограничиваем ширину до 50
                worksheet_users.column_dimensions[column_letter].width = adjusted_width
            
            campaigns_df.to_excel(writer, sheet_name='Campaigns', index=False)
            
            # Автоподбор ширины столбцов для Campaigns
            worksheet_campaigns = writer.sheets['Campaigns']
            for column in worksheet_campaigns.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Ограничиваем ширину до 50
                worksheet_campaigns.column_dimensions[column_letter].width = adjusted_width
            
            referrals_df.to_excel(writer, sheet_name='Referrals', index=False)
            
            # Автоподбор ширины столбцов для Referrals
            worksheet_referrals = writer.sheets['Referrals']
            for column in worksheet_referrals.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Ограничиваем ширину до 50
                worksheet_referrals.column_dimensions[column_letter].width = adjusted_width
            
            tickets_df.to_excel(writer, sheet_name='Tickets', index=False)
            
            # Автоподбор ширины столбцов для Tickets
            worksheet_tickets = writer.sheets['Tickets']
            for column in worksheet_tickets.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Ограничиваем ширину до 50
                worksheet_tickets.column_dimensions[column_letter].width = adjusted_width
            
            draw_results_df.to_excel(writer, sheet_name='DrawResults', index=False)
            
            # Автоподбор ширины столбцов для DrawResults
            worksheet_draw_results = writer.sheets['DrawResults']
            for column in worksheet_draw_results.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Ограничиваем ширину до 50
                worksheet_draw_results.column_dimensions[column_letter].width = adjusted_width
            
            audit_logs_df.to_excel(writer, sheet_name='AuditLogs', index=False)
            
            # Автоподбор ширины столбцов для AuditLogs
            worksheet_audit_logs = writer.sheets['AuditLogs']
            for column in worksheet_audit_logs.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Ограничиваем ширину до 50
                worksheet_audit_logs.column_dimensions[column_letter].width = adjusted_width
        
        print(f"Данные успешно экспортированы в {filename}")
        print(f"Всего пользователей: {len(users_df)}")
        print(f"Всего кампаний: {len(campaigns_df)}")
        print(f"Всего рефералов: {len(referrals_df)}")
        print(f"Всего билетов: {len(tickets_df)}")
        print(f"Всего результатов розыгрыша: {len(draw_results_df)}")
        print(f"Всего логов аудита: {len(audit_logs_df)}")
        
        return filename
        
    except Exception as e:
        print(f"Ошибка при экспорте данных: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await engine.dispose()


async def export_statistics():
    """
    Экспортирует только статистику в Excel файл
    """
    import os
    settings = get_settings()
    engine = build_engine(settings)
    
    try:
        async with AsyncSession(engine) as session:
            # Получаем статистику пользователей
            users_result = await session.execute(select(User))
            users_data = users_result.scalars().all()
            
            total_users = len(users_data)
            blocked_users = sum(1 for u in users_data if u.is_blocked)
            active_users = total_users - blocked_users
            
            # Получаем статистику кампаний
            campaigns_result = await session.execute(select(Campaign))
            campaigns_data = campaigns_result.scalars().all()
            
            total_campaigns = len(campaigns_data)
            active_campaigns = sum(1 for c in campaigns_data if c.status.value == 'active')
            finished_campaigns = sum(1 for c in campaigns_data if c.status.value == 'finished')
            draft_campaigns = sum(1 for c in campaigns_data if c.status.value == 'draft')
            
            # Получаем статистику рефералов
            referrals_result = await session.execute(select(Referral))
            referrals_data = referrals_result.scalars().all()
            
            total_referrals = len(referrals_data)
            pending_referrals = sum(1 for r in referrals_data if r.status.value == 'pending')
            verified_referrals = sum(1 for r in referrals_data if r.status.value == 'verified')
            rejected_referrals = sum(1 for r in referrals_data if r.status.value == 'rejected')
            
            # Получаем статистику билетов
            tickets_result = await session.execute(select(Ticket))
            tickets_data = tickets_result.scalars().all()
            
            total_tickets = len(tickets_data)
            
            # Получаем статистику результатов розыгрыша
            draw_results_result = await session.execute(select(DrawResult))
            draw_results_data = draw_results_result.scalars().all()
            
            total_draw_results = len(draw_results_data)
            
            # Создаем DataFrame для общей статистики
            stats_data = {
                'Метрика': [
                    'Всего пользователей',
                    'Активные пользователи',
                    'Заблокированные пользователи',
                    'Всего кампаний',
                    'Активные кампании',
                    'Завершенные кампании',
                    'Черновики кампаний',
                    'Всего рефералов',
                    'Ожидающие подтверждения',
                    'Подтвержденные рефералы',
                    'Отклоненные рефералы',
                    'Всего билетов',
                    'Всего результатов розыгрыша'
                ],
                'Значение': [
                    total_users,
                    active_users,
                    blocked_users,
                    total_campaigns,
                    active_campaigns,
                    finished_campaigns,
                    draft_campaigns,
                    total_referrals,
                    pending_referrals,
                    verified_referrals,
                    rejected_referrals,
                    total_tickets,
                    total_draw_results
                ]
            }
            
            stats_df = pd.DataFrame(stats_data)
            
            # Экспорт в Excel
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"exports/statistics_export_{timestamp}.xlsx"
            
            os.makedirs('exports', exist_ok=True)
            
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                stats_df.to_excel(writer, sheet_name='Статистика', index=False)
                
                # Добавляем лист с пользователями
                users_list = []
                for user in users_data:
                    user_dict = {
                        'id': user.id,
                        'telegram_id': user.telegram_id,
                        'username': user.username,
                        'ref_code': user.ref_code,
                        'referred_by': user.referred_by,
                        'age': user.age,
                        'favorite_sport': user.favorite_sport,
                        'is_blocked': user.is_blocked,
                        'created_at': _strip_tz(user.created_at)
                    }
                    users_list.append(user_dict)
                
                users_df = pd.DataFrame(users_list)
                users_df.to_excel(writer, sheet_name='Пользователи', index=False)
        
        print(f"Статистика успешно экспортирована в {filename}")
        print(f"Всего пользователей: {total_users}")
        print(f"Всего кампаний: {total_campaigns}")
        print(f"Всего рефералов: {total_referrals}")
        
        return filename
        
    except Exception as e:
        print(f"Ошибка при экспорте статистики: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Экспорт данных из БД в Excel')
    parser.add_argument('--stats-only', action='store_true', help='Экспортировать только статистику')
    parser.add_argument('--output-dir', default='exports', help='Директория для экспорта')
    
    args = parser.parse_args()
    
    if args.stats_only:
        asyncio.run(export_statistics())
    else:
        asyncio.run(export_data_to_excel(args.output_dir))