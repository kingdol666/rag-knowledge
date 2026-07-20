import { TreeFileSystemService } from '../services/tree-file-system-service'
import { getTreeStorageAbsolutePath } from './runtime-paths'

let serviceInstance: TreeFileSystemService | null = null

export const getTreeFileSystemService = async (): Promise<TreeFileSystemService> => {
  if (!serviceInstance) {
    serviceInstance = new TreeFileSystemService(getTreeStorageAbsolutePath())
    await serviceInstance.initialize()
  }
  return serviceInstance
}
