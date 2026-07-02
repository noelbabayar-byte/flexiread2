# Sayfa Değiştirme Sorunu Analizi

## Tespit Edilen Sorunlar

### Sorun 1: `goToPreviousPage` ve `goToNextPage` fonksiyonlarında `totalPages` bağımlılığı yanlış
- `ReaderView.tsx` satır 157: `container.scrollHeight / totalPages` hesaplama yapılırken, `totalPages` React state'den alınır
- Ancak tüm sayfalar render edildiğinde (satır 85: `engine.renderVisiblePages(bookContent.pages)`), `scrollHeight` gerçek render edilen DOM yüksekliğidir
- Bu hesaplama mantıklı ancak sorun şu ki: `currentPage` state'i React state'inden alınır ve scroll event'leri ile güncellenir

### Sorun 2: `data-page-number` attribute ile sayfa bulunurken sayfa elementinin render edilmiş olması gerekir
- `goToPreviousPage` / `goToNextPage`: önce `querySelector` ile `[data-page-number="${prevPage}"]` arar
- Eğer sayfa bulunamazsa, `scrollHeight / totalPages` ile pozisyon hesaplayıp scroll yapar
- Ancak virtual scroll nedeniyle sayfalar DOM'dan silinebilir!

### Sorun 3: Virtual scroll pruning - sayfalar siliniyor
- `engine.ts` satır 344-366: `pruneOutOfBufferBlocks` fonksiyonu, virtual scroll buffer'ı dışındaki sayfaları DOM'dan siliyor
- Başlangıçta buffer: `startPageIndex: 0, endPageIndex: 2` (sadece 3 sayfa!)
- Yani sayfa 5'e gitmek istediğinde, sayfa 4 DOM'da olmayabilir
- `goToNextPage` fonksiyonu önce `querySelector` arar, bulamazsa scroll hesaplar
- Scroll hesaplaması `scrollHeight / totalPages` ile yapılıyor ama sayfalar silindiği için `scrollHeight` doğru olmayabilir

### Sorun 4: `currentPage` state'i güncellenme gecikmesi
- `currentPage` state'i `onProgressChange` callback'inden gelen IntersectionObserver verilerine göre güncelleniyor
- `goToPreviousPage` / `goToNextPage` fonksiyonlarında `currentPage` state'i kullanılıyor ama bu state gecikmeli güncellenebilir

### Sorun 5: `pageHeight` hesaplama mantığı hatalı
- `const pageHeight = container.scrollHeight / totalPages` - bu hesaplama tüm sayfaların aynı yükseklikte olduğunu varsayar
- Sayfalar farklı içerik miktarına sahip olduğundan yükseklikleri farklıdır
- Sayfa 1 1000px, sayfa 2 500px olabilir - ortalama yükseklik ile hesaplama yanlış pozisyona gider

### Ana Sorun: Virtual scroll buffer çok küçük + sayfa silinmesi + `currentPage` state gecikmesi
1. Kullanıcı "Sonraki Sayfa" butonuna tıklar
2. `goToNextPage` çağrılır, `currentPage` = 1 (örn.)
3. Sayfa 2 DOM'da var (buffer içinde), `scrollIntoView` çalışır
4. IntersectionObserver scroll'u algılar, `onProgressChange` callback'ini çağırır
5. `currentPage` state'i 2'ye güncellenir
6. Ama sanal scroll pruning ile sayfa 1 silinebilir!
7. Bir sonraki tıklamada `currentPage` state'i 2'dir ama sayfa 2 DOM'dan silinmiş olabilir
8. O zaman `scrollHeight / totalPages` ile hesaplama yapılır ama bu yanlış pozisyona gider

### Çözüm Stratejisi:
1. `goToPreviousPage` / `goToNextPage` fonksiyonlarında React `currentPage` state'i yerine engine/state manager'dan güncel progress'i okumalı
2. Sayfa bulunamazsa, sayfa elementini DOM'a yeniden render etmeli (state manager'dan veriyi alıp)
3. Virtual scroll buffer'ını genişletmeli veya sayfa değiştirme için özel bir render mekanizması eklemeli
4. `pageHeight` hesaplamasını her sayfa için ayrı yapmalı
