#include "WarInterfacePages.h"
#include "WarInterfaceCatalog.h"
#include "WarInterfaceStyle.h"
#include "WarContentSubsystem.h"
#include "WarPlayerController.h"
#include "WarCityNpc.h"
#include "WarQuestNpc.h"
#include "WarCraftingStation.h"
#include "WarResourceNode.h"
#include "WarZonePortal.h"
#include "WarZoneAnchor.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMeshActor.h"
#include "EngineUtils.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Text/STextBlock.h"
#include "Rendering/DrawElements.h"
#include "Styling/CoreStyle.h"

namespace
{
    struct FAtlasState
    {
        FWarInterfaceCatalog Catalog;
        FString Level=TEXT("Zone"),Selected=TEXT("aegis_capital"),Current=TEXT("aegis_capital"),Hover;
        FVector Origin=FVector::ZeroVector;
        FVector2D Pan=FVector2D::ZeroVector;
        double Zoom=1;
        TSet<FString> Layers{TEXT("Exits")};
        TArray<FWarMapMarker> NativeMarkers;
        TArray<FBox2D> Buildings;
        TMap<FString,FVector2D> Graph;
        void Fit() { Zoom=1; Pan=FVector2D::ZeroVector; }
        bool Native() const { return Level==TEXT("Zone") && Selected==Current; }
        void Out() { Level=Level==TEXT("Zone") ? TEXT("Route") : TEXT("Campaign"); Fit(); }
        void Inspect(const FString& Id) { Selected=Id; Level=Level==TEXT("Campaign") ? TEXT("Route") : TEXT("Zone"); Fit(); }
        TArray<const FWarMapZone*> VisibleZones() const
        {
            TArray<const FWarMapZone*> Result;
            const auto* Focus=Catalog.FindZone(Selected);
            for (const auto& Zone:Catalog.Zones)
            {
                bool Include=Level==TEXT("Campaign") || !Focus || Zone.Lane==Focus->Lane;
                if (!Include && Focus) for (const auto& SameLane:Catalog.Zones)
                    if (SameLane.Lane==Focus->Lane && SameLane.Destinations.Contains(Zone.Id)) { Include=true; break; }
                if (Include) Result.Add(&Zone);
            }
            return Result;
        }
        void LayoutGraph()
        {
            int32 Centre=0;
            for (const auto& Zone:Catalog.Zones)
            {
                if (Zone.Lane==TEXT("central")) { Graph.Add(Zone.Id,FVector2D(600,80+Centre++*110)); continue; }
                if (Zone.Role==TEXT("boss_lair")) continue;
                const bool Aegis=Zone.Realm==TEXT("aegis"),West=Zone.Lane.EndsWith(TEXT("west"));
                const int32 Tier=FMath::Clamp(FCString::Atoi(*Zone.Tier.RightChop(1)),1,3);
                Graph.Add(Zone.Id,FVector2D(West ? 315 : 885,Aegis ? 80+Tier*110 : 850-Tier*110));
            }
            for (const auto& Zone:Catalog.Zones)
            {
                if (Zone.Role!=TEXT("boss_lair")) continue;
                for (const auto& Destination:Zone.Destinations)
                    if (const auto* Point=Graph.Find(Destination))
                    { Graph.Add(Zone.Id,*Point+FVector2D(Zone.Lane.EndsWith(TEXT("west")) ? -280 : 280,0)); break; }
            }
        }
    };

    class SWarAtlasCanvas : public SLeafWidget
    {
    public:
        SLATE_BEGIN_ARGS(SWarAtlasCanvas) {} SLATE_END_ARGS()
        void Construct(const FArguments&,TSharedRef<FAtlasState> Data,AWarPlayerController* PC)
        { State=Data; Owner=PC; SetClipping(EWidgetClipping::ClipToBounds); }
        virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D(720,370); }
        virtual void Tick(const FGeometry& Geometry,double Time,float Delta) override
        {
            SLeafWidget::Tick(Geometry,Time,Delta);
            if (!Owner.IsValid() || !Owner->GetPawn() || Time<NextRefresh) return;
            NextRefresh=Time+1;
            const FVector Player=Owner->GetPawn()->GetActorLocation();
            const auto* CurrentAnchor=AWarZoneAnchor::FindAt(Owner->GetWorld(),Player);
            if (CurrentAnchor)
            {
                const FString Previous=State->Current;
                State->Current=CurrentAnchor->ZoneId.ToString();
                State->Origin=CurrentAnchor->ZoneOrigin;
                if (State->Selected==Previous && State->Level==TEXT("Zone")) State->Selected=State->Current;
            }
            double Nearest=TNumericLimits<double>::Max();
            for (TActorIterator<AWarZonePortal> It(Owner->GetWorld());It;++It)
            {
                if (CurrentAnchor) break;
                FString ZoneId,Target;
                if (!It->RouteId.ToString().Split(TEXT("_to_"),&ZoneId,&Target)) continue;
                const auto* Zone=State->Catalog.FindZone(ZoneId); if (!Zone) continue;
                const auto* Marker=Zone->Markers.FindByPredicate([&](const auto& M) { return M.Id==It->RouteId.ToString(); });
                if (!Marker) continue;
                const double Distance=FVector::DistSquared(Player,It->GetActorLocation());
                if (Distance<Nearest)
                {
                    Nearest=Distance;State->Current=ZoneId;
                    State->Origin=It->GetActorLocation()-FVector(-Marker->Position.Y*100,Marker->Position.X*100,0);
                    State->Origin.Z=0;
                }
            }
            State->NativeMarkers.Reset(); State->Buildings.Reset();
            const auto Position=[this](FVector Value) { Value-=State->Origin; return FVector2D(Value.Y/100,-Value.X/100); };
            for (TActorIterator<AActor> It(Owner->GetWorld());It;++It)
            {
                if (It->IsHidden()) continue;
                if (CurrentAnchor && !AWarZoneAnchor::ContainsPoint(CurrentAnchor->ZoneOrigin,CurrentAnchor->HalfSize,It->GetActorLocation())) continue;
                FString Label,Layer;
                if (const auto* Npc=Cast<AWarCityNpc>(*It)) { Label=Npc->DisplayName;Layer=TEXT("People"); }
                else if (const auto* Quest=Cast<AWarQuestNpc>(*It)) { Label=Quest->NpcId.ToString();Layer=TEXT("Quests"); }
                else if (const auto* Station=Cast<AWarCraftingStation>(*It)) { Label=Station->StationKind.ToString();Layer=TEXT("Crafting"); }
                else if (const auto* Resource=Cast<AWarResourceNode>(*It)) { Label=Resource->NodeId.ToString();Layer=TEXT("Resources"); }
                else if (const auto* Portal=Cast<AWarZonePortal>(*It)) { Label=Portal->DestinationLabel.ToString();Layer=TEXT("Exits"); }
                if (!Layer.IsEmpty()) State->NativeMarkers.Add({It->GetName(),Label,Layer,Position(It->GetActorLocation())});
                if (It->ActorHasTag(TEXT("WarCapitalBuilding")) || It->ActorHasTag(TEXT("WarCreatedBuilding")))
                {
                    const FBox Bounds=It->GetComponentsBoundingBox(true);
                    if (Bounds.IsValid) { FBox2D Footprint(ForceInit); Footprint+=Position(Bounds.Min);Footprint+=Position(Bounds.Max);State->Buildings.Add(Footprint); }
                }
            }
        }
        virtual FReply OnMouseWheel(const FGeometry& Geometry,const FPointerEvent& Event) override
        {
            const FVector2D Cursor=Geometry.AbsoluteToLocal(Event.GetScreenSpacePosition());
            const FVector2D World=Unproject(Cursor,Geometry.GetLocalSize());
            State->Zoom=FMath::Clamp(State->Zoom*(Event.GetWheelDelta()>0 ? 1.25 : 0.8),0.5,8.0);
            State->Pan+=Cursor-Project(World,Geometry.GetLocalSize());
            return FReply::Handled();
        }
        virtual FReply OnMouseButtonDown(const FGeometry& Geometry,const FPointerEvent& Event) override
        {
            if (Event.GetEffectingButton()==EKeys::RightMouseButton) { State->Out(); return FReply::Handled(); }
            if (Event.GetEffectingButton()!=EKeys::LeftMouseButton) return FReply::Unhandled();
            DragStart=LastMouse=Geometry.AbsoluteToLocal(Event.GetScreenSpacePosition());bDragging=true;bMoved=false;
            return FReply::Handled().CaptureMouse(SharedThis(this));
        }
        virtual FReply OnMouseMove(const FGeometry& Geometry,const FPointerEvent& Event) override
        {
            const FVector2D Mouse=Geometry.AbsoluteToLocal(Event.GetScreenSpacePosition());
            if (bDragging) { State->Pan+=Mouse-LastMouse;bMoved|=FVector2D::Distance(Mouse,DragStart)>4; }
            LastMouse=Mouse;
            State->Hover=Hit(Mouse,Geometry.GetLocalSize(),false);
            return FReply::Handled();
        }
        virtual FReply OnMouseButtonUp(const FGeometry& Geometry,const FPointerEvent& Event) override
        {
            if (Event.GetEffectingButton()!=EKeys::LeftMouseButton || !bDragging) return FReply::Unhandled();
            bDragging=false;
            if (!bMoved && State->Level!=TEXT("Zone"))
            {
                const auto Id=Hit(Geometry.AbsoluteToLocal(Event.GetScreenSpacePosition()),Geometry.GetLocalSize(),true);
                if (!Id.IsEmpty()) State->Inspect(Id);
            }
            return FReply::Handled().ReleaseMouseCapture();
        }
        virtual void OnMouseCaptureLost(const FCaptureLostEvent&) override { bDragging=false; }
        virtual int32 OnPaint(const FPaintArgs&,const FGeometry& Geometry,const FSlateRect&,FSlateWindowElementList& Elements,
            int32 Layer,const FWidgetStyle&,bool) const override
        {
            const FVector2D Size=Geometry.GetLocalSize();
            const auto* Brush=FCoreStyle::Get().GetBrush("WhiteBrush");
            FSlateDrawElement::MakeBox(Elements,Layer,Geometry.ToPaintGeometry(),Brush,ESlateDrawEffect::None,WarInterfaceStyle::Sidebar);
            const auto Text=[&](const FString& Value,FVector2D P,FLinearColor Colour,int32 FontSize=11) {
                FSlateDrawElement::MakeText(Elements,Layer+4,Geometry.ToPaintGeometry(FVector2D(400,80),FSlateLayoutTransform(P)),Value,
                    FCoreStyle::GetDefaultFontStyle("Regular",FontSize),ESlateDrawEffect::None,Colour);
            };
            const auto Line=[&](const TArray<FVector2D>& Points,FLinearColor Colour,float Width=1) {
                if (Points.Num()<2) return;
                FSlateDrawElement::MakeLines(Elements,Layer+1,Geometry.ToPaintGeometry(),Points,ESlateDrawEffect::None,Colour,true,Width);
            };
            if (State->Level==TEXT("Zone"))
            {
                const auto* Zone=State->Catalog.FindZone(State->Selected);
                if (!Zone) { Text(TEXT("Map data unavailable"),FVector2D(16,16),WarInterfaceStyle::Text);return Layer+4; }
                if (State->Native())
                    for (const auto& Box:State->Buildings)
                    {
                        const FVector2D A=Project(Box.Min,Size),B=Project(Box.Max,Size);
                        Line({A,FVector2D(B.X,A.Y),B,FVector2D(A.X,B.Y),A},FLinearColor(0.22f,0.27f,0.3f));
                    }
                else for (const auto& Path:Zone->Paths)
                {
                    TArray<FVector2D> Points;for (const auto& P:Path) Points.Add(Project(P,Size));
                    Line(Points,WarInterfaceStyle::Line,2);
                }
                const auto& Markers=State->Native() ? State->NativeMarkers : Zone->Markers;
                for (const auto& Marker:Markers)
                {
                    if (!State->Layers.Contains(Marker.Layer)) continue;
                    const FVector2D P=Project(Marker.Position,Size);
                    const FLinearColor Colour=Marker.Layer==TEXT("Exits") ? WarInterfaceStyle::Gold : Marker.Layer==TEXT("Quests") ? FLinearColor::Yellow
                        : Marker.Layer==TEXT("Resources") ? FLinearColor(0.35f,0.65f,0.28f) : Marker.Layer==TEXT("Enemies") ? FLinearColor(0.8f,0.15f,0.15f) : FLinearColor(0.2f,0.65f,0.8f);
                    FSlateDrawElement::MakeBox(Elements,Layer+2,Geometry.ToPaintGeometry(FVector2D(6,6),FSlateLayoutTransform(P-FVector2D(3,3))),Brush,ESlateDrawEffect::None,Colour);
                }
                if (State->Native() && Owner.IsValid() && Owner->GetPawn())
                {
                    const FVector Player=Owner->GetPawn()->GetActorLocation()-State->Origin;
                    const FVector2D P=Project(FVector2D(Player.Y/100,-Player.X/100),Size);
                    FSlateDrawElement::MakeBox(Elements,Layer+3,Geometry.ToPaintGeometry(FVector2D(9,9),FSlateLayoutTransform(P-FVector2D(4.5,4.5))),Brush,ESlateDrawEffect::None,WarInterfaceStyle::Text);
                    Text(TEXT("You"),P+FVector2D(8,4),WarInterfaceStyle::Text);
                }
                Text(TEXT("N"),FVector2D(Size.X-24,12),WarInterfaceStyle::Gold,13);
            }
            else
            {
                const auto Visible=State->VisibleZones();
                TSet<FString> Ids;for (const auto* Zone:Visible) Ids.Add(Zone->Id);
                for (const auto* Zone:Visible) for (const auto& Next:Zone->Destinations)
                    if (Ids.Contains(Next) && Zone->Id<Next && State->Graph.Contains(Zone->Id) && State->Graph.Contains(Next))
                        Line({Project(State->Graph[Zone->Id],Size),Project(State->Graph[Next],Size)},WarInterfaceStyle::Line,1.5f);
                for (const auto* Zone:Visible)
                {
                    const auto* Point=State->Graph.Find(Zone->Id);if (!Point) continue;
                    const FVector2D P=Project(*Point,Size),Extent=NodeSize(Size);
                    const FLinearColor Colour=Zone->Realm==TEXT("aegis") ? FLinearColor(0.04f,0.16f,0.24f) : FLinearColor(0.23f,0.045f,0.06f);
                    FSlateDrawElement::MakeBox(Elements,Layer+2,Geometry.ToPaintGeometry(Extent,FSlateLayoutTransform(P-Extent*0.5)),Brush,ESlateDrawEffect::None,Colour);
                    TArray<FString> Words; Zone->Name.ParseIntoArrayWS(Words);
                    FString Label; int32 Column=0;
                    for (const auto& Word:Words)
                    {
                        if (Column && Column+1+Word.Len()>15) { Label+=TEXT("\n");Column=0; }
                        else if (Column) { Label+=TEXT(" ");++Column; }
                        Label+=Word;Column+=Word.Len();
                    }
                    Text(Label,P-Extent*0.5+FVector2D(4,2),Zone->Id==State->Selected ? WarInterfaceStyle::Gold : WarInterfaceStyle::Text,9);

                }
            }
            if (!State->Hover.IsEmpty())
            {
                FSlateDrawElement::MakeBox(Elements,Layer+5,Geometry.ToPaintGeometry(FVector2D(Size.X,26),FSlateLayoutTransform(FVector2D(0,Size.Y-26))),Brush,ESlateDrawEffect::None,WarInterfaceStyle::Background);
                FSlateDrawElement::MakeText(Elements,Layer+6,Geometry.ToPaintGeometry(Size,FSlateLayoutTransform(FVector2D(10,Size.Y-22))),State->Hover,FCoreStyle::GetDefaultFontStyle("Regular",12),ESlateDrawEffect::None,WarInterfaceStyle::Gold);
            }
            return Layer+6;
        }
    private:
        TSharedPtr<FAtlasState> State;
        TWeakObjectPtr<AWarPlayerController> Owner;
        double NextRefresh=0;
        FVector2D DragStart,LastMouse;
        bool bDragging=false,bMoved=false;
        FBox2D Bounds() const
        {
            if (State->Level==TEXT("Zone"))
            {
                const auto* Zone=State->Catalog.FindZone(State->Selected);
                const double Half=Zone ? Zone->Size/2 : 400;
                if (State->Native() && !State->Buildings.IsEmpty())
                {
                    FBox2D Loaded(ForceInit);
                    for (const auto& Building:State->Buildings)
                        if (Building.GetCenter().GetAbsMax()<Half) { Loaded+=Building.Min;Loaded+=Building.Max; }
                    if (Loaded.bIsValid) return Loaded.ExpandBy(20);
                }
                return FBox2D(FVector2D(-Half,-Half),FVector2D(Half,Half));
            }
            FBox2D Result(ForceInit);
            for (const auto* Zone:State->VisibleZones()) if (const auto* Point=State->Graph.Find(Zone->Id)) Result+=*Point;
            return Result.bIsValid ? Result.ExpandBy(110) : FBox2D(FVector2D(0,0),FVector2D(1200,930));
        }
        FVector2D Scale(FVector2D Size) const
        {
            const FVector2D Extent=Bounds().GetSize();
            FVector2D Result((Size.X-30)/FMath::Max(Extent.X,1.),(Size.Y-30)/FMath::Max(Extent.Y,1.));
            if (State->Level==TEXT("Zone")) Result=FVector2D(FMath::Min(Result.X,Result.Y));
            return Result*State->Zoom;
        }
        FVector2D Project(FVector2D Point,FVector2D Size) const { return (Point-Bounds().GetCenter())*Scale(Size)+Size*0.5+State->Pan; }
        FVector2D Unproject(FVector2D Point,FVector2D Size) const { return (Point-Size*0.5-State->Pan)/Scale(Size)+Bounds().GetCenter(); }
        FVector2D NodeSize(FVector2D Size) const { const auto S=Scale(Size); return FVector2D(FMath::Max(88.,240*S.X),FMath::Max(28.,80*S.Y)); }
        FString Hit(FVector2D Mouse,FVector2D Size,bool IdOnly) const
        {
            if (State->Level!=TEXT("Zone"))
                for (const auto* Zone:State->VisibleZones())
                    if (const auto* Point=State->Graph.Find(Zone->Id))
                    {
                        const FVector2D P=Project(*Point,Size),Half=NodeSize(Size)*0.5;
                        if (FMath::Abs(Mouse.X-P.X)<Half.X && FMath::Abs(Mouse.Y-P.Y)<Half.Y)
                            return IdOnly ? Zone->Id : Zone->Name+TEXT(" | ")+Zone->Tier+TEXT(" | click to inspect");
                    }
            const auto* Zone=State->Catalog.FindZone(State->Selected);
            if (State->Level==TEXT("Zone") && Zone)
            {
                const auto& Markers=State->Native() ? State->NativeMarkers : Zone->Markers;
                const FWarMapMarker* Best=nullptr;double Distance=144;
                for (const auto& Marker:Markers)
                {
                    const double D=FVector2D::DistSquared(Mouse,Project(Marker.Position,Size));
                    if (State->Layers.Contains(Marker.Layer) && D<Distance) { Distance=D;Best=&Marker; }
                }
                if (Best) return Best->Label+TEXT(" | ")+Best->Layer;
            }
            return FString();
        }
    };

    class SWarAtlas : public SCompoundWidget
    {
    public:
        SLATE_BEGIN_ARGS(SWarAtlas) {} SLATE_END_ARGS()
        void Construct(const FArguments&,AWarPlayerController* Controller,bool Campaign,bool Clean)
        {
            Data=MakeShared<FAtlasState>();
            const auto* Content=Controller->GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
            Data->Catalog=FWarInterfaceCatalog::Parse(Content ? Content->GetInterfaceCatalogSource() : nullptr);
            Data->LayoutGraph();if (Clean) Data->Layers.Reset();if (Campaign) Data->Level=TEXT("Campaign");
            auto Bar=SNew(SHorizontalBox);
            const auto Button=[this](const FString& Label,TFunction<void()> Action) -> TSharedRef<SWidget> {
                return SNew(SButton).ButtonStyle(&WarInterfaceStyle::Button()).ContentPadding(FMargin(10,7))
                    .OnClicked_Lambda([Action] { Action();return FReply::Handled(); })
                    [SNew(STextBlock).Text(FText::FromString(Label)).ColorAndOpacity(WarInterfaceStyle::Text)];
            };
            for (const FString Level:{FString(TEXT("Zone")),FString(TEXT("Route")),FString(TEXT("Campaign"))})
                Bar->AddSlot().AutoWidth().Padding(0,0,5,0)[Button(Level,[this,Level] { Data->Level=Level;Data->Fit(); })];
            Bar->AddSlot().AutoWidth().Padding(8,0)[Button(TEXT("Fit"),[this] { Data->Fit(); })];
            Bar->AddSlot().AutoWidth().Padding(0,0,5,0)[Button(TEXT("Current"),[this] { Data->Selected=Data->Current;Data->Level=TEXT("Zone");Data->Fit(); })];
            Bar->AddSlot().AutoWidth()[Button(TEXT("Clean Map"),[this] { Data->Layers.Reset();Data->Level=TEXT("Zone"); })];
            auto LayerBar=SNew(SWrapBox).UseAllottedSize(true);
            for (const FString Layer:{FString(TEXT("People")),FString(TEXT("Quests")),FString(TEXT("Crafting")),FString(TEXT("Resources")),FString(TEXT("Enemies")),FString(TEXT("Exits")),FString(TEXT("Objectives")),FString(TEXT("Places"))})
                LayerBar->AddSlot().Padding(0,0,5,5)[SNew(SButton).ButtonStyle(&WarInterfaceStyle::Button()).ContentPadding(6)
                    .OnClicked_Lambda([this,Layer] { if (Data->Layers.Contains(Layer)) Data->Layers.Remove(Layer);else Data->Layers.Add(Layer);return FReply::Handled(); })
                    [SNew(STextBlock).Text(FText::FromString(Layer)).Font(FCoreStyle::GetDefaultFontStyle("Regular",11))
                        .ColorAndOpacity_Lambda([this,Layer] { return Data->Layers.Contains(Layer) ? WarInterfaceStyle::Gold : WarInterfaceStyle::Muted; })]];
            ChildSlot[SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[Bar]
                + SVerticalBox::Slot().AutoHeight().Padding(0,8)[SNew(STextBlock).ColorAndOpacity(WarInterfaceStyle::Gold).Text_Lambda([this] {
                    const auto* Zone=Data->Catalog.FindZone(Data->Selected);
                    return FText::FromString(Data->Level+TEXT(" / ")+(Zone ? Zone->Name : Data->Selected)+TEXT(" / ")+FString::Printf(TEXT("%.0f%%"),Data->Zoom*100)); })]
                + SVerticalBox::Slot().AutoHeight()[SNew(SWarAtlasCanvas,Data.ToSharedRef(),Controller)]
                + SVerticalBox::Slot().AutoHeight().Padding(0,8)[LayerBar]
                + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).AutoWrapText(true).Font(FCoreStyle::GetDefaultFontStyle("Regular",12)).ColorAndOpacity(WarInterfaceStyle::Muted)
                    .Text_Lambda([this] { return FText::FromString(Data->Native()
                        ? TEXT("Loaded native geometry. Drag to pan; wheel to zoom; hover for labels. White marks your position.")
                        : TEXT("Authored campaign reference; realm colours show homeland, not live ownership. Click to inspect deeper; right-click to go back. Native availability varies by zone.")); })]];
        }
    private:
        TSharedPtr<FAtlasState> Data;
    };
}
TSharedRef<SWidget> WarBuildAtlas(AWarPlayerController* Controller,bool Campaign,bool Clean) { return SNew(SWarAtlas,Controller,Campaign,Clean); }
