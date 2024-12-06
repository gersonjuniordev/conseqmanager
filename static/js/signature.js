document.addEventListener('DOMContentLoaded', function() {
    const documentId = window.location.pathname.split('/').pop();
    const signaturePad = new SignaturePad(document.getElementById('signature-pad'), {
        backgroundColor: 'rgb(255, 255, 255)'
    });
    const signaturePreview = document.getElementById('signature-preview');
    const pdfContainer = document.getElementById('pdf-container');
    const pdfViewer = document.getElementById('pdf-viewer');
    let signaturePosition = { x: 0, y: 0 };
    let pdfScale = 1.5;

    // Carregar PDF com escala apropriada
    async function loadPDF() {
        const docId = window.location.pathname.split('/').pop();
        const pdfUrl = `/view/${docId}`;
        
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        try {
            const loadingTask = pdfjsLib.getDocument(pdfUrl);
            const pdf = await loadingTask.promise;
            const page = await pdf.getPage(1);
            
            // Ajustar escala baseado no tamanho da tela
            const viewport = page.getViewport({ scale: pdfScale });
            const containerWidth = pdfContainer.clientWidth;
            pdfScale = containerWidth / viewport.width;
            
            const adjustedViewport = page.getViewport({ scale: pdfScale });
            pdfViewer.width = adjustedViewport.width;
            pdfViewer.height = adjustedViewport.height;
            
            const context = pdfViewer.getContext('2d');
            await page.render({
                canvasContext: context,
                viewport: adjustedViewport
            }).promise;
        } catch (error) {
            console.error('Erro ao carregar PDF:', error);
        }
    }

    // Melhorar o drag and drop da assinatura
    function initDragAndDrop() {
        const preview = signaturePreview;
        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;

        preview.addEventListener('mousedown', dragStart);
        preview.addEventListener('touchstart', dragStart, { passive: false });
        document.addEventListener('mousemove', drag);
        document.addEventListener('touchmove', drag, { passive: false });
        document.addEventListener('mouseup', dragEnd);
        document.addEventListener('touchend', dragEnd);

        function dragStart(e) {
            e.preventDefault();
            if (e.type === 'touchstart') {
                initialX = e.touches[0].clientX - preview.offsetLeft;
                initialY = e.touches[0].clientY - preview.offsetTop;
            } else {
                initialX = e.clientX - preview.offsetLeft;
                initialY = e.clientY - preview.offsetTop;
            }
            isDragging = true;
            preview.style.cursor = 'grabbing';
        }

        function drag(e) {
            if (isDragging) {
                e.preventDefault();
                
                if (e.type === 'touchmove') {
                    currentX = e.touches[0].clientX - initialX;
                    currentY = e.touches[0].clientY - initialY;
                } else {
                    currentX = e.clientX - initialX;
                    currentY = e.clientY - initialY;
                }

                const rect = pdfContainer.getBoundingClientRect();
                currentX = Math.min(Math.max(0, currentX), rect.width - preview.offsetWidth);
                currentY = Math.min(Math.max(0, currentY), rect.height - preview.offsetHeight);

                preview.style.left = currentX + 'px';
                preview.style.top = currentY + 'px';

                signaturePosition.x = (currentX / rect.width) * 100;
                signaturePosition.y = (currentY / rect.height) * 100;
            }
        }

        function dragEnd() {
            isDragging = false;
            preview.style.cursor = 'grab';
        }
    }

    // Carregar o PDF quando a página carregar
    loadPDF();

    document.getElementById('clear').addEventListener('click', function() {
        signaturePad.clear();
    });

    document.getElementById('position').addEventListener('click', function() {
        if (signaturePad.isEmpty()) {
            alert('Por favor, faça sua assinatura primeiro.');
            return;
        }

        const signatureData = signaturePad.toDataURL();
        signaturePreview.innerHTML = `<img src="${signatureData}" style="max-width: 200px;">`;
        signaturePreview.style.display = 'block';
        initDragAndDrop();
    });

    document.getElementById('save').addEventListener('click', async function() {
        try {
            if (signaturePad.isEmpty()) {
                alert('Por favor, faça sua assinatura primeiro.');
                return;
            }

            const form = document.getElementById('signerForm');
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            const formData = new FormData(form);
            const signatureData = {
                signature: signaturePad.toDataURL(),
                position_x: signaturePosition.x || 0,
                position_y: signaturePosition.y || 0,
                name: formData.get('name'),
                email: formData.get('email'),
                cpf: formData.get('cpf')
            };

            console.log('Enviando dados:', signatureData);  // Debug

            const response = await fetch(`/sign/${documentId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(signatureData)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Erro ao assinar documento');
            }
            
            alert('Documento assinado com sucesso!');
            window.location.href = `/verify/${documentId}`;
            
        } catch (error) {
            console.error('Erro:', error);
            alert(error.message || 'Erro ao assinar o documento');
        }
    });
});
