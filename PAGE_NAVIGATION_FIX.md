# Sayfa Değiştirme Sorunu Düzeltmesi

## Tespit Edilen Sorunlar

### 1. Virtual Scroll Pruning (Sayfa Silinmesi)

Engine.ts dosyasında bulunan `updateVirtualScroll()` ve `pruneOutOfBufferBlocks()` fonksiyonları, scroll pozisyonuna göre görünmeyen sayfaları DOM'dan siliyordu. Başlangıç buffer'ı sadece 3 sayfa idi (`startPageIndex: 0, endPageIndex: 2`). Kullanıcı 4. sayfaya veya sonrasına geçmek istediğinde, o sayfa DOM'dan silinmiş olabiliyordu.

### 2. Hatalı `pageHeight` Hesaplaması

`ReaderView.tsx` dosyasındaki `goToPreviousPage` ve `goToNextPage` fonksiyonlarında, sayfa elementinin DOM'da bulunamaması durumunda alternatif olarak:

```typescript
const pageHeight = container.scrollHeight / totalPages;
container.scrollTo({ top: pageHeight * (prevPage - 1), behavior: 'smooth' });
```

hesaplaması kullanılıyordu. Bu hesaplama **tüm sayfaların aynı yükseklikte olduğunu** varsayar, oysa her sayfa farklı içerik uzunluğuna sahiptir. Bu nedenle hesaplanan pozisyon yanlış sayfaya giderdi.

### 3. React State Gecikmesi

`currentPage` React state'i, IntersectionObserver callback'inden gecikmeli güncelleniyordu. Buton tıklaması yapıldığında, state henüz güncellenmemiş olabiliyordu. Ayrıca `goToPreviousPage` fonksiyonunun dependency array'inde `totalPages` da bulunuyordu, bu da gereksiz re-renders'a yol açıyordu.

## Uygulanan Düzeltmeler

### Dosya: `frontend/src/reader/engine.ts`

Yeni bir `navigateToPage()` metodu eklendi:

- Hedef sayfa DOM'da varsa, doğrudan `scrollIntoView()` ile kaydırır
- Hedef sayfa DOM'da yoksa (virtual scroll pruning nedeniyle), **tüm sayfaları yeniden render eder** ve ardından kaydırır
- İlerlemeyi state manager'a günceller

Bu yaklaşım, hatalı `scrollHeight/totalPages` matematiğini tamamen ortadan kaldırır ve her zaman doğru sayfaya gider.

### Dosya: `frontend/src/components/ReaderView.tsx`

- `goToPreviousPage` ve `goToNextPage` fonksiyonları artık doğrudan `engine.navigateToPage()` metodunu çağırıyor
- Eski `querySelector` + `scrollHeight` mantığı tamamen kaldırıldı
- Fallback olarak state manager `updateProgress()` çağrısı eklendi
- `goToPreviousPage` dependency array'inden `totalPages` kaldırıldı (sadece `currentPage` bağımlı)
- Initialization sırasında state manager'dan ilk sayfa numarası okunup state'e set edildi

## Teknik Detaylar

| Önceki Yaklaşım | Yeni Yaklaşım |
|---|---|
| `querySelector` ile sayfa bulma | `engine.navigateToPage()` metodu |
| `scrollHeight / totalPages` ile pozisyon hesaplama | Tüm sayfaları render et + `scrollIntoView()` |
| React state'e bağımlı | Engine ref üzerinden doğrudan erişim |
| Virtual scroll pruning bozulma | Pruning + re-render stratejisi |

## Sonuç

Sayfa değiştirme butonları artık:
1. Önce sayfanın DOM'da olup olmadığını kontrol eder
2. Varsa doğrudan kaydırır
3. Yoksa tüm sayfaları yeniden render eder ve kaydırır
4. İlerleme durumunu güncel tutar

Bu düzeltme, hem küçük hem de büyük kitaplar için çalışır ve virtual scroll performans optimizasyonunu korur.
