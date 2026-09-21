#include "WarCityNpc.h"
#include "WarCityServices.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Pawn.h"
#include "Components/TextRenderComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"

AWarCityNpc::AWarCityNpc()
{
    bReplicates = true; PrimaryActorTick.bCanEverTick = true; PrimaryActorTick.TickInterval=.1f;
    Nameplate=CreateDefaultSubobject<UTextRenderComponent>(TEXT("CityNameplate"));
    Nameplate->SetupAttachment(GetRootComponent());Nameplate->SetRelativeLocation(FVector(0,0,210));
    Nameplate->SetHorizontalAlignment(EHTA_Center);Nameplate->SetWorldSize(18);
    Nameplate->SetTextRenderColor(FColor(210,202,179));Nameplate->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}
void AWarCityNpc::BeginPlay()
{
    Super::BeginPlay();
    FString RoleLabel=CityRole.ToString().Replace(TEXT("_"),TEXT(" "));
    Nameplate->SetText(FText::FromString(DisplayName+TEXT("\n")+RoleLabel));
}
void AWarCityNpc::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);
    if(auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0))
    {
        const FVector Delta=Camera->GetCameraLocation()-Nameplate->GetComponentLocation();
        Nameplate->SetVisibility(Delta.SizeSquared()<FMath::Square(1800.f));
        Nameplate->SetWorldRotation(Delta.Rotation());
    }
}
FName AWarCityNpc::GetService() const { return WarCityServices::ServiceForNpc(NpcId); }
bool AWarCityNpc::CanInteract(const APawn* Pawn) const
{
    const auto* Mesh = GetSkeletalMeshComponent();
    return IsValid(Pawn) && Pawn->GetWorld() == GetWorld() && !GetService().IsNone()
        && !IsActorBeingDestroyed() && !IsHidden() && Mesh && Mesh->IsVisible() && Mesh->GetSkeletalMeshAsset()
        && FVector::DistSquared(Pawn->GetActorLocation(), GetActorLocation()) < FMath::Square(400.0);
}
