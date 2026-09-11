
import { usePatientContext } from '../components/Layout';
import { Card, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Select } from '@shared/ui/Select';
import { FileText, Download, Building, Calendar, HardDrive, FileImage, File } from 'lucide-react';
import { EmptyState } from '@shared/ui/EmptyState';

export default function Documents() {
  const { documents, docFilterHospital, setDocFilterHospital, docFilterType, setDocFilterType, handleDownload } = usePatientContext();

  const filteredDocuments = documents.filter(d => 
    (!docFilterHospital || d.hospital?.name === docFilterHospital) && 
    (!docFilterType || d.document_type === docFilterType)
  );

  const getFileIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'pdf': return <FileText className="h-8 w-8 text-rose-500" />;
      case 'image': return <FileImage className="h-8 w-8 text-blue-500" />;
      default: return <File className="h-8 w-8 text-slate-400" />;
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-500">
      
      {/* Filters & Header Bar */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-800 m-0">My Medical Records</h3>
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          <Select 
            className="w-full sm:w-48 bg-slate-50" 
            value={docFilterHospital} 
            onChange={e => setDocFilterHospital(e.target.value)}
          >
            <option value="">All Hospitals</option>
            {Array.from(new Set(documents.map(d => d.hospital?.name))).filter(Boolean).map(hName => (
              <option key={hName as string} value={hName as string}>{hName as string}</option>
            ))}
          </Select>
          <Select 
            className="w-full sm:w-40 bg-slate-50" 
            value={docFilterType} 
            onChange={e => setDocFilterType(e.target.value)}
          >
            <option value="">All File Types</option>
            {Array.from(new Set(documents.map(d => d.document_type))).filter(Boolean).map(tName => (
              <option key={tName as string} value={tName as string}>{tName as string}</option>
            ))}
          </Select>
        </div>
      </div>
      
      {/* Document Grid */}
      {filteredDocuments.length === 0 ? (
        <EmptyState 
          icon={<FileText className="h-12 w-12" />} 
          title="No documents found" 
          description="Try adjusting your filters or check back later after your doctor uploads your records."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDocuments.map(doc => (
            <Card key={doc.id} className="overflow-hidden hover:shadow-md transition-shadow group">
              <CardContent className="p-0">
                <div className="p-5 flex items-start gap-4">
                  <div className="p-3 bg-slate-50 rounded-lg shrink-0 group-hover:bg-primary/5 transition-colors">
                    {getFileIcon(doc.document_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-base font-semibold text-slate-900 truncate mb-1" title={doc.title}>
                      {doc.title}
                    </h4>
                    <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1 truncate">
                      <Building className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">{doc.hospital?.name || 'Unknown Hospital'}</span>
                    </div>
                    {doc.description && (
                      <p className="text-sm text-slate-600 line-clamp-2 mt-2 leading-snug">
                        {doc.description}
                      </p>
                    )}
                  </div>
                </div>
                
                <div className="bg-slate-50 px-5 py-3 border-t border-slate-100 flex items-center justify-between">
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <Calendar className="h-3.5 w-3.5" />
                      {new Date(doc.created_at).toLocaleDateString()}
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <HardDrive className="h-3.5 w-3.5" />
                      {(doc.file_size / 1024).toFixed(1)} KB
                    </div>
                  </div>
                  
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="gap-2 shrink-0 group-hover:border-primary/50 group-hover:text-primary transition-colors"
                    onClick={() => handleDownload(doc.id, doc.original_filename)}
                  >
                    <Download className="h-4 w-4" />
                    Download
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
