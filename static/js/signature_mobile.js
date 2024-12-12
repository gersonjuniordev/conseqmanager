document.addEventListener('DOMContentLoaded', function() {
    const documentId = window.location.pathname.split('/').pop();
    const signaturePad = new SignaturePad(document.getElementById('signature-pad'), {
        backgroundColor: 'rgb(255, 255, 255)'
    });
    const pdfContainer = document.getElementById('pdf-container');
    const pdfViewer = document.getElementById('pdf-viewer');
    let currentPage = 1;
    let pdfDoc = null;

    let signaturePosition = { x: 10, y: 90 }; // Posição padrão
    const modal = document.getElementById('positionModal');
    const closeButton = document.querySelector('.close-button');
    const confirmButton = document.getElementById('confirmPosition');
    const signaturePreview = document.getElementById('signature-preview');

    // Carregar PDF
    async function loadPDF() {
        const pdfUrl = `/view/${documentId}`;
        
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        try {
            // Primeiro, tentar buscar o PDF
            const response = await fetch(pdfUrl);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Converter resposta para ArrayBuffer
            const pdfData = await response.arrayBuffer();
            
            // Carregar PDF com pdf.js
            const loadingTask = pdfjsLib.getDocument({data: pdfData});
            pdfDoc = await loadingTask.promise;
            
            // Adicionar controles de navegação se houver mais de uma página
            if (pdfDoc.numPages > 1) {
                addPageControls();
            }
            
            // Renderizar primeira página
            await renderPage(1);
            
        } catch (error) {
            console.error('Erro ao carregar PDF:', error);
            alert('Erro ao carregar o documento. Por favor, tente novamente.');
        }
    }

    // Renderizar página específica
    async function renderPage(pageNumber) {
        try {
            const page = await pdfDoc.getPage(pageNumber);
            const viewport = page.getViewport({ scale: 1.0 });
            
            // Ajustar escala para caber na tela
            const containerWidth = pdfContainer.clientWidth;
            const scale = containerWidth / viewport.width;
            const scaledViewport = page.getViewport({ scale });

            // Configurar canvas
            pdfViewer.width = scaledViewport.width;
            pdfViewer.height = scaledViewport.height;
            
            const renderContext = {
                canvasContext: pdfViewer.getContext('2d'),
                viewport: scaledViewport,
                enableWebGL: true
            };

            await page.render(renderContext).promise;
            currentPage = pageNumber;
            
            // Atualizar contador de páginas
            if (document.getElementById('pageInfo')) {
                document.getElementById('pageInfo').textContent = 
                    `Página ${currentPage} de ${pdfDoc.numPages}`;
            }
        } catch (error) {
            console.error('Erro ao renderizar página:', error);
            alert('Erro ao exibir a página do documento.');
        }
    }

    // Adicionar controles de navegação
    function addPageControls() {
        const controls = document.createElement('div');
        controls.className = 'pdf-controls';
        controls.innerHTML = `
            <button id="prevPage" class="button button-secondary">
                <i class="bi bi-chevron-left"></i>
            </button>
            <span id="pageInfo">Página 1 de ${pdfDoc.numPages}</span>
            <button id="nextPage" class="button button-secondary">
                <i class="bi bi-chevron-right"></i>
            </button>
        `;
        
        pdfContainer.insertBefore(controls, pdfViewer);
        
        // Eventos dos botões
        document.getElementById('prevPage').addEventListener('click', () => {
            if (currentPage > 1) {
                renderPage(currentPage - 1);
            }
        });
        
        document.getElementById('nextPage').addEventListener('click', () => {
            if (currentPage < pdfDoc.numPages) {
                renderPage(currentPage + 1);
            }
        });
    }

    // Limpar assinatura
    document.getElementById('clear').addEventListener('click', function() {
        signaturePad.clear();
    });

    // Botão de posicionamento
    document.getElementById('position').addEventListener('click', function() {
        if (signaturePad.isEmpty()) {
            alert('Por favor, faça sua assinatura primeiro');
            return;
        }
        openPositioningModal();
    });

    // Abrir modal de posicionamento
    async function openPositioningModal() {
        modal.style.display = 'block';
        const pdfViewerModal = document.getElementById('pdf-viewer-modal');
        
        // Mostrar preview da assinatura
        signaturePreview.innerHTML = `<img src="${signaturePad.toDataURL()}" draggable="false">`;
        signaturePreview.style.display = 'block';
        
        // Renderizar PDF no modal
        await renderPDFInModal(pdfViewerModal);
        
        // Inicializar drag and drop
        initDragAndDrop();
    }

    // Renderizar PDF no modal
    async function renderPDFInModal(canvas) {
        try {
            const page = await pdfDoc.getPage(currentPage);
            const viewport = page.getViewport({ scale: 1.0 });
            
            // Ajustar escala para caber na tela do modal
            const containerWidth = canvas.parentElement.clientWidth;
            const scale = containerWidth / viewport.width;
            const scaledViewport = page.getViewport({ scale });

            canvas.width = scaledViewport.width;
            canvas.height = scaledViewport.height;
            
            await page.render({
                canvasContext: canvas.getContext('2d'),
                viewport: scaledViewport
            }).promise;
        } catch (error) {
            console.error('Erro ao renderizar PDF no modal:', error);
        }
    }

    // Inicializar drag and drop
    function initDragAndDrop() {
        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;
        let scale = 1;
        let currentScale = 1;
        let initialDistance = 0;
        let transformOrigin = { x: '50%', y: '50%' };

        signaturePreview.addEventListener('touchstart', handleTouchStart, { passive: false });
        document.addEventListener('touchmove', handleTouchMove, { passive: false });
        document.addEventListener('touchend', handleTouchEnd);

        function handleTouchStart(e) {
            e.preventDefault();
            
            if (e.touches.length === 1) {
                // Modo de arrasto
                isDragging = true;
                initialX = e.touches[0].clientX - signaturePreview.offsetLeft;
                initialY = e.touches[0].clientY - signaturePreview.offsetTop;
            } 
            else if (e.touches.length === 2) {
                // Modo de redimensionamento
                isDragging = false;
                initialDistance = getDistance(
                    e.touches[0].clientX,
                    e.touches[0].clientY,
                    e.touches[1].clientX,
                    e.touches[1].clientY
                );
                currentScale = scale;
                
                // Calcular o ponto central entre os dois dedos
                const centerX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
                const centerY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
                
                // Converter para posição relativa ao elemento
                const rect = signaturePreview.getBoundingClientRect();
                transformOrigin.x = ((centerX - rect.left) / rect.width) * 100 + '%';
                transformOrigin.y = ((centerY - rect.top) / rect.height) * 100 + '%';
                
                signaturePreview.style.transformOrigin = `${transformOrigin.x} ${transformOrigin.y}`;
            }
        }

        function handleTouchMove(e) {
            e.preventDefault();
            
            if (isDragging && e.touches.length === 1) {
                // Lógica de arrasto
                currentX = e.touches[0].clientX - initialX;
                currentY = e.touches[0].clientY - initialY;

                const container = document.querySelector('.pdf-container-modal');
                const rect = container.getBoundingClientRect();
                
                // Ajustar limites considerando a escala
                const scaledWidth = signaturePreview.offsetWidth * scale;
                const scaledHeight = signaturePreview.offsetHeight * scale;
                
                currentX = Math.min(Math.max(0, currentX), rect.width - scaledWidth);
                currentY = Math.min(Math.max(0, currentY), rect.height - scaledHeight);

                signaturePreview.style.left = currentX + 'px';
                signaturePreview.style.top = currentY + 'px';

                signaturePosition.x = (currentX / rect.width) * 100;
                signaturePosition.y = (currentY / rect.height) * 100;
            } 
            else if (e.touches.length === 2) {
                // Lógica de redimensionamento
                const currentDistance = getDistance(
                    e.touches[0].clientX,
                    e.touches[0].clientY,
                    e.touches[1].clientX,
                    e.touches[1].clientY
                );
                
                scale = currentScale * (currentDistance / initialDistance);
                scale = Math.min(Math.max(0.5, scale), 2);
                
                signaturePreview.style.transform = `scale(${scale})`;
                signaturePreview.dataset.scale = scale;
            }
        }

        function handleTouchEnd() {
            isDragging = false;
        }

        function getDistance(x1, y1, x2, y2) {
            return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
        }
    }

    // Fechar modal
    closeButton.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Confirmar posição
    confirmButton.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Salvar assinatura
    document.getElementById('save').addEventListener('click', async function() {
        try {
            if (signaturePad.isEmpty()) {
                alert('Por favor, faça sua assinatura primeiro');
                return;
            }

            const form = document.getElementById('signerForm');
            if (!form.checkValidity()) {
                form.reportValidity();
                return;
            }

            const termsCheckbox = document.getElementById('terms');
            if (!termsCheckbox.checked) {
                alert('Você precisa aceitar os termos para continuar');
                return;
            }

            const formData = new FormData(form);
            const signatureData = {
                signature: signaturePad.toDataURL(),
                position_x: signaturePosition.x,
                position_y: signaturePosition.y,
                scale: parseFloat(signaturePreview.dataset.scale || 1),
                name: formData.get('name'),
                email: formData.get('email'),
                cpf: formData.get('cpf')
            };

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

    // Inicializar
    loadPDF();
}); 