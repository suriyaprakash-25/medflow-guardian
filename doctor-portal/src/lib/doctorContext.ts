import { useOutletContext } from 'react-router-dom';

import type { OutletContextType } from '../components/Layout';

export function useDoctorContext() {
  return useOutletContext<OutletContextType>();
}
