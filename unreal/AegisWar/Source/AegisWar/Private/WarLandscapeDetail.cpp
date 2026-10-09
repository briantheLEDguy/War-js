#include "WarLandscapeDetail.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

AWarLandscapeDetail::AWarLandscapeDetail()
{
    SetReplicates(false);
    PrimaryActorTick.bCanEverTick=false;
    Details=CreateDefaultSubobject<UHierarchicalInstancedStaticMeshComponent>(TEXT("LandscapeDetails"));
    SetRootComponent(Details);
    Details->SetMobility(EComponentMobility::Static);
    Details->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Details->SetGenerateOverlapEvents(false);
    Details->SetCanEverAffectNavigation(false);
    Details->SetCastShadow(false);
    Details->SetCullDistances(3500,12000);
}

bool AWarLandscapeDetail::Configure(UStaticMesh* Mesh,const TArray<FTransform>& Transforms)
{
    if(!Mesh||Mesh->GetNumLODs()<1||Transforms.Num()<1||Transforms.Num()>MaximumInstances)return false;
    for(const FTransform& Transform:Transforms)
    {
        const FVector P=Transform.GetTranslation(),S=Transform.GetScale3D();
        if(Transform.ContainsNaN()||!Transform.GetRotation().IsNormalized()||P.GetAbsMax()>250000
            ||S.GetMin()<.15||S.GetMax()>2)return false;
    }
    Details->ClearInstances();
    Details->SetStaticMesh(Mesh);
    Details->AddInstances(Transforms,false);
    return Details->GetInstanceCount()==Transforms.Num();
}

void AWarLandscapeDetail::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer)Details->SetVisibility(false,true);
}
